/**
 * Singleton client for in-browser (Pyodide) league simulations.
 *
 * Owns one simulation.worker.js instance per page load and acts as its
 * watchdog: Pyodide has no in-run interrupt without SharedArrayBuffer (the
 * app serves no COOP/COEP headers), so a stuck run — an agent looping
 * forever — is ended by terminating the worker and booting a fresh one.
 *
 * A run is chunked: the JS side asks the worker for a few hundred games at a
 * time, so progress updates and cancellation are observable between chunks
 * (the worker thread is blocked while synchronous Python runs). Cancelling
 * finishes the in-flight chunk, then finalizes with capped=true — partial
 * results are kept, mirroring what the old Celery task did when it hit its
 * server-side time budget.
 *
 * Resolution kinds (there is deliberately no "fallback" kind — the Celery
 * simulation path no longer exists):
 *   { kind: "local", envelope }  — the harness ran; envelope is the old
 *     simulation task's shape, including status:"error" outcomes (no
 *     loadable players, an agent crashing every game).
 *   { kind: "error", reason }    — the runtime itself failed (boot failure,
 *     watchdog timeout, worker crash); nothing to save.
 *
 * State machine: idle → booting → ready ⇄ running, terminal `failed`.
 * A boot failure is terminal for the session; a run failure reboots the
 * worker so the next run starts clean.
 */

const BOOT_TIMEOUT_MS = 30000; // bigger payload than exercises: engine tree writes
const SETUP_TIMEOUT_MS = 20000; // player loading + the one verbose feedback game
const CHUNK_TIMEOUT_MS = 20000; // a chunk is ~250ms of games; 20s means a hung agent
const FINALIZE_TIMEOUT_MS = 10000;

const TARGET_CHUNK_MS = 250; // keep progress + cancel responsive
const INITIAL_CHUNK_SIZE = 5;
const MAX_CHUNK_SIZE = 1000;

const runner = {
  state: 'idle', // idle | booting | ready | running | failed
  worker: null,
  bootPromise: null,
  failureReason: null,
  nextRunId: 1,
  // FIFO so a second run request during a run waits instead of colliding.
  queue: Promise.resolve(),
};

function spawnWorker() {
  return new Worker(new URL('./simulation.worker.js', import.meta.url), {
    type: 'module',
  });
}

function markFailed(reason) {
  runner.state = 'failed';
  runner.failureReason = reason;
  runner.worker?.terminate();
  runner.worker = null;
  console.warn(`Pyodide simulation runner unavailable: ${reason}`);
}

/**
 * Boot the worker if it isn't already up. Resolves true when ready, false
 * when the runner is (or becomes) failed. Safe to call repeatedly — the
 * simulation panel calls it on mount to hide the boot latency.
 */
export function ensureSimulationRunner() {
  if (runner.state === 'ready' || runner.state === 'running') {
    return Promise.resolve(true);
  }
  if (runner.state === 'failed') return Promise.resolve(false);
  if (runner.bootPromise) return runner.bootPromise;

  runner.state = 'booting';
  runner.bootPromise = new Promise((resolve) => {
    const worker = spawnWorker();
    runner.worker = worker;

    const bootTimer = setTimeout(() => {
      markFailed('boot-timeout');
      resolve(false);
    }, BOOT_TIMEOUT_MS);

    const settle = (ok, reason) => {
      clearTimeout(bootTimer);
      if (ok) {
        runner.state = 'ready';
      } else {
        markFailed(reason);
      }
      resolve(ok);
    };

    worker.onmessage = (event) => {
      if (event.data.type === 'ready') settle(true);
      else if (event.data.type === 'init-error') {
        settle(false, `boot-failed: ${event.data.error}`);
      }
    };
    worker.onerror = (event) => {
      settle(false, `worker-crashed: ${event.message || 'unknown'}`);
    };

    worker.postMessage({ type: 'init' });
  }).finally(() => {
    runner.bootPromise = null;
  });
  return runner.bootPromise;
}

/** Terminate the current worker and boot a replacement for the next run. */
function rebootWorker() {
  runner.worker?.terminate();
  runner.worker = null;
  runner.state = 'idle';
  ensureSimulationRunner();
}

/** Reject-on-timeout request/response exchange with the worker. */
function exchange(worker, runId, request, expectType, timeoutMs) {
  return new Promise((resolve, reject) => {
    let settled = false;

    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      reject(new Error(`${request.type}-timeout after ${timeoutMs}ms`));
    }, timeoutMs);

    const settle = (fn, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      fn(value);
    };

    worker.onmessage = (event) => {
      const message = event.data;
      if (message.runId !== runId) return; // stale message from a dead run
      if (message.type === expectType) {
        settle(resolve, JSON.parse(message.resultJson));
      } else if (message.type === 'worker-error') {
        settle(reject, new Error(`run-infra-error: ${message.error}`));
      }
    };
    worker.onerror = (event) => {
      settle(reject, new Error(`worker-crashed: ${event.message || 'unknown'}`));
    };

    worker.postMessage({ runId, ...request });
  });
}

async function runOnWorker(
  { gameName, submissions, numSimulations, customRewards, onProgress },
  control
) {
  const runId = runner.nextRunId++;
  runner.state = 'running';
  const worker = runner.worker;

  try {
    const setup = await exchange(
      worker,
      runId,
      {
        type: 'setup-run',
        gameName,
        submissionsJson: JSON.stringify(submissions ?? {}),
        customRewardsJson: customRewards ? JSON.stringify(customRewards) : '',
        requestedSimulations: numSimulations,
      },
      'setup-done',
      SETUP_TIMEOUT_MS
    );
    if (setup.status === 'error') {
      runner.state = 'ready';
      return { kind: 'local', envelope: setup };
    }

    let completed = 0;
    let chunkSize = INITIAL_CHUNK_SIZE;
    onProgress?.({ completed, requested: numSimulations });

    while (completed < numSimulations && !control.cancelled) {
      const count = Math.min(chunkSize, numSimulations - completed);
      const started = performance.now();
      const chunk = await exchange(
        worker,
        runId,
        { type: 'run-chunk', count },
        'chunk-done',
        CHUNK_TIMEOUT_MS
      );
      if (chunk.status === 'error') {
        // A game blew up mid-run (agent exception): the old task aborted the
        // whole run the same way. The interpreter is still healthy.
        runner.state = 'ready';
        return { kind: 'local', envelope: chunk };
      }
      completed = chunk.completed;
      onProgress?.({ completed, requested: numSimulations });

      const elapsed = Math.max(performance.now() - started, 1);
      chunkSize = Math.max(
        1,
        Math.min(Math.round((count * TARGET_CHUNK_MS) / elapsed), MAX_CHUNK_SIZE)
      );
    }

    const envelope = await exchange(
      worker,
      runId,
      { type: 'finalize', capped: completed < numSimulations },
      'run-complete',
      FINALIZE_TIMEOUT_MS
    );
    runner.state = 'ready';
    return { kind: 'local', envelope };
  } catch (error) {
    rebootWorker();
    return { kind: 'error', reason: String(error?.message || error) };
  }
}

/**
 * Run one league simulation in the browser.
 *
 * Returns { promise, cancel }: `promise` resolves { kind: "local", envelope }
 * or { kind: "error", reason } — see the module docstring. `cancel()` stops
 * launching new chunks; the run then finalizes with what it has
 * (envelope.simulation_results.capped === true). Runs are serialized FIFO.
 */
export function startLeagueSimulation(params) {
  const control = { cancelled: false };

  const promise = runner.queue.then(async () => {
    const ready = await ensureSimulationRunner();
    if (!ready) {
      return {
        kind: 'error',
        reason: runner.failureReason || 'runner-unavailable',
      };
    }
    return runOnWorker(params, control);
  });
  // Keep the queue alive even if a task rejects unexpectedly.
  runner.queue = promise.catch(() => {});

  return {
    promise,
    cancel: () => {
      control.cancelled = true;
    },
  };
}
