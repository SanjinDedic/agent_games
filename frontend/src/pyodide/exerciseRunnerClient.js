/**
 * Singleton client for in-browser (Pyodide) exercise and snippet execution.
 *
 * Owns one pyodideExercise.worker.js instance per page load and acts as its
 * watchdog: Pyodide has no in-run interrupt without SharedArrayBuffer (the
 * app serves no COOP/COEP headers), so a stuck run is ended by terminating
 * the worker and booting a fresh one. Exercise submissions and lesson
 * snippet runs share the worker, the FIFO queue, and the watchdog — they
 * differ only in the run message and the timeout envelope shape.
 *
 * The contract with usePyodideExerciseSubmit / usePyodideSnippetRun is the
 * resolution kind:
 *   { kind: "local", envelope }   — Pyodide ran; envelope is the normalized
 *     result (identical shape to the Celery worker's), including
 *     status:"error" outcomes like a crash or the watchdog timeout. Never
 *     falls back: Celery would fail the same way.
 *   { kind: "fallback", reason }  — Pyodide itself couldn't run (boot
 *     failure, infra crash mid-run); the caller must submit through the
 *     Celery path with this reason so the fallback is counted server-side.
 *
 * State machine: idle → booting → ready ⇄ running, terminal `failed`.
 * A boot failure is terminal for the session — every later submission falls
 * back. A run failure (timeout/crash) reboots the worker and the next
 * submission tries Pyodide again.
 */

const BOOT_TIMEOUT_MS = 15000;
const RUN_TIMEOUT_MS = 5000;

// Same phrasing as the Celery worker's EXERCISE_TIMEOUT_MESSAGE /
// SNIPPET_TIMEOUT_MESSAGE (backend/exercise_worker/tasks.py) with this
// runtime's honest budget.
const EXERCISE_TIMEOUT_MESSAGE =
  `Your code consumes too much time - the tests did not finish within ` +
  `${RUN_TIMEOUT_MS / 1000} seconds. It may be stuck in a loop.`;

const SNIPPET_TIMEOUT_MESSAGE =
  `Your code did not finish within ${RUN_TIMEOUT_MS / 1000} seconds. ` +
  `It may be stuck in a loop.`;

// Build-time kill switch: set VITE_PYODIDE_EXERCISES=false to force every
// exercise submission AND lesson snippet run through the Celery path (no
// fallback tagging — it's not a fallback, it's the configured path).
export const isPyodideEnabled = () =>
  import.meta.env.VITE_PYODIDE_EXERCISES !== 'false';

const exerciseTimeoutEnvelope = () => ({
  status: 'error',
  message: EXERCISE_TIMEOUT_MESSAGE,
  passed: false,
  test_results: [],
  duration_ms: null,
  traceback: null,
  stdout: null,
});

const snippetTimeoutEnvelope = () => ({
  status: 'error',
  message: SNIPPET_TIMEOUT_MESSAGE,
  stdout: null,
  traceback: null,
  duration_ms: null,
});

const runner = {
  state: 'idle', // idle | booting | ready | running | failed
  worker: null,
  bootPromise: null,
  failureReason: null,
  nextRunId: 1,
  // FIFO so a second submit during a run waits instead of colliding.
  queue: Promise.resolve(),
};

function spawnWorker() {
  return new Worker(new URL('./pyodideExercise.worker.js', import.meta.url), {
    type: 'module',
  });
}

function markFailed(reason) {
  runner.state = 'failed';
  runner.failureReason = reason;
  runner.worker?.terminate();
  runner.worker = null;
  console.warn(`Pyodide exercise runner unavailable: ${reason}`);
}

/**
 * Boot the worker if it isn't already up. Resolves true when ready, false
 * when the runner is (or becomes) failed. Safe to call repeatedly — the
 * Tutorial page calls it on mount to hide the boot latency.
 */
export function ensureRunner() {
  if (!isPyodideEnabled()) return Promise.resolve(false);
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
  ensureRunner();
}

function runOnWorker(payload, timeoutEnvelope) {
  const runId = runner.nextRunId++;
  runner.state = 'running';
  const worker = runner.worker;

  return new Promise((resolve) => {
    let settled = false;

    const runTimer = setTimeout(() => {
      if (settled) return;
      settled = true;
      // Student code stuck in a loop: a local outcome, not a fallback —
      // Celery would time the same code out too.
      rebootWorker();
      resolve({ kind: 'local', envelope: timeoutEnvelope() });
    }, RUN_TIMEOUT_MS);

    const settle = (outcome, { reboot = false } = {}) => {
      if (settled) return;
      settled = true;
      clearTimeout(runTimer);
      if (reboot) {
        rebootWorker();
      } else {
        runner.state = 'ready';
      }
      resolve(outcome);
    };

    worker.onmessage = (event) => {
      const message = event.data;
      if (message.runId !== runId) return; // stale message from a dead run
      if (message.type === 'result') {
        settle({ kind: 'local', envelope: JSON.parse(message.resultJson) });
      } else if (message.type === 'run-error') {
        settle(
          { kind: 'fallback', reason: `run-infra-error: ${message.error}` },
          { reboot: true }
        );
      }
    };
    worker.onerror = (event) => {
      settle(
        {
          kind: 'fallback',
          reason: `worker-crashed: ${event.message || 'unknown'}`,
        },
        { reboot: true }
      );
    };

    worker.postMessage({ ...payload, runId });
  });
}

/** Queue one run behind any in-flight one; fall back if the runner is down. */
function enqueueRun(payload, timeoutEnvelope) {
  const task = runner.queue.then(async () => {
    const ready = await ensureRunner();
    if (!ready) {
      return {
        kind: 'fallback',
        reason: runner.failureReason || 'runner-unavailable',
      };
    }
    return runOnWorker(payload, timeoutEnvelope);
  });
  // Keep the queue alive even if a task rejects unexpectedly.
  runner.queue = task.catch(() => {});
  return task;
}

/**
 * Run one exercise submission in the browser.
 * Resolves { kind: "local", envelope } or { kind: "fallback", reason } —
 * see the module docstring. Runs are serialized FIFO.
 */
export function runExercise({ code, entryFunction, testCode }) {
  return enqueueRun(
    { type: 'run', code, entryFunction, testCode },
    exerciseTimeoutEnvelope
  );
}

/**
 * Run one lesson snippet in the browser. Same contract and FIFO queue as
 * runExercise; the envelope is the snippet shape
 * { status, message, stdout, traceback, duration_ms }.
 */
export function runSnippet({ code }) {
  return enqueueRun({ type: 'run-snippet', code }, snippetTimeoutEnvelope);
}
