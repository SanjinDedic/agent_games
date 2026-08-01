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
 *     failure, failed health probe, infra crash mid-run); the caller must
 *     submit through the server fallback with this reason so the fallback is
 *     counted server-side.
 *
 * State machine: idle → booting → probing → ready ⇄ running, terminal
 * `failed` (reachable from booting or probing). `ready` means the runtime
 * has *proven* it can execute Python: after boot, a health probe runs a
 * trivial snippet through the normal run-snippet path under
 * PROBE_TIMEOUT_MS — the only check that catches a worker that boots but
 * whose runtime is wedged. A boot or probe failure is terminal for the
 * session — every later submission falls back. A run failure
 * (timeout/crash) reboots the worker, and the next submission boots and
 * probes again.
 *
 * UI observes the machine via getRunnerStatus / subscribeRunnerStatus
 * (useSyncExternalStore-compatible: the snapshot object is cached and only
 * replaced on a state transition).
 */

const BOOT_TIMEOUT_MS = 15000;
const RUN_TIMEOUT_MS = 5000;
const PROBE_TIMEOUT_MS = 500;
const PROBE_ATTEMPTS = 2;
const PROBE_CODE = '1+1';

// Same phrasing as the fallback executor's EXERCISE_TIMEOUT_MESSAGE /
// SNIPPET_TIMEOUT_MESSAGE (backend/fallback_lambda/executor.py) with this
// runtime's honest budget.
const EXERCISE_TIMEOUT_MESSAGE =
  `Your code consumes too much time - the tests did not finish within ` +
  `${RUN_TIMEOUT_MS / 1000} seconds. It may be stuck in a loop.`;

const SNIPPET_TIMEOUT_MESSAGE =
  `Your code did not finish within ${RUN_TIMEOUT_MS / 1000} seconds. ` +
  `It may be stuck in a loop.`;

// Build-time kill switch: set VITE_PYODIDE_EXERCISES=false to force every
// exercise submission AND lesson snippet run through the server fallback (no
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
  state: 'idle', // idle | booting | probing | ready | running | failed
  worker: null,
  bootPromise: null,
  failureReason: null,
  nextRunId: 1,
  // FIFO so a second submit during a run waits instead of colliding.
  queue: Promise.resolve(),
};

const listeners = new Set();
// Cached so getRunnerStatus returns a stable reference between transitions —
// useSyncExternalStore treats a fresh object per call as an endless update.
let statusSnapshot = null;

function notify() {
  statusSnapshot = null;
  listeners.forEach((listener) => listener());
}

function setState(next) {
  if (runner.state === next) return;
  runner.state = next;
  notify();
}

/** Snapshot of the runner for UI (status dot); see subscribeRunnerStatus. */
export function getRunnerStatus() {
  if (!statusSnapshot) {
    statusSnapshot = {
      state: runner.state,
      failureReason: runner.failureReason,
      pyodideEnabled: isPyodideEnabled(),
    };
  }
  return statusSnapshot;
}

/** Listen for state transitions. Returns an unsubscribe function. */
export function subscribeRunnerStatus(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function spawnWorker() {
  return new Worker(new URL('./pyodideExercise.worker.js', import.meta.url), {
    type: 'module',
  });
}

function markFailed(reason) {
  // Reason first so the notify inside setState publishes a coherent snapshot.
  runner.failureReason = reason;
  setState('failed');
  runner.worker?.terminate();
  runner.worker = null;
  console.warn(`Pyodide exercise runner unavailable: ${reason}`);
}

/**
 * Wait for the worker to finish loading Pyodide and the harness.
 * Resolves { ok: true } or { ok: false, reason }. Never rejects; resolves
 * at most once (later worker events are no-ops on the settled promise).
 */
function bootPhase(worker) {
  return new Promise((resolve) => {
    const bootTimer = setTimeout(() => {
      resolve({ ok: false, reason: 'boot-timeout' });
    }, BOOT_TIMEOUT_MS);

    const settle = (outcome) => {
      clearTimeout(bootTimer);
      resolve(outcome);
    };

    worker.onmessage = (event) => {
      if (event.data.type === 'ready') settle({ ok: true });
      else if (event.data.type === 'init-error') {
        settle({ ok: false, reason: `boot-failed: ${event.data.error}` });
      }
    };
    worker.onerror = (event) => {
      settle({
        ok: false,
        reason: `worker-crashed: ${event.message || 'unknown'}`,
      });
    };

    worker.postMessage({ type: 'init' });
  });
}

/**
 * One health-probe attempt: run PROBE_CODE through the normal run-snippet
 * path under PROBE_TIMEOUT_MS. Resolves 'pass' | 'timeout' | 'error'.
 * Uses the shared runId counter so a stale probe result can never collide
 * with a later run (and vice versa — the runId filters discard strays).
 */
function probeOnce(worker) {
  const runId = runner.nextRunId++;
  return new Promise((resolve) => {
    let settled = false;

    const probeTimer = setTimeout(() => {
      if (settled) return;
      settled = true;
      resolve('timeout');
    }, PROBE_TIMEOUT_MS);

    const settle = (outcome, detail) => {
      if (settled) return;
      settled = true;
      clearTimeout(probeTimer);
      // The reason sent to telemetry stays a bounded token ('probe-error');
      // the underlying detail is only logged.
      if (detail) console.warn(`Pyodide health probe failed: ${detail}`);
      resolve(outcome);
    };

    worker.onmessage = (event) => {
      const message = event.data;
      if (message.runId !== runId) return; // stale message from an earlier attempt
      if (message.type === 'result') {
        let envelope;
        try {
          envelope = JSON.parse(message.resultJson);
        } catch (error) {
          settle('error', `unparseable result: ${error}`);
          return;
        }
        if (envelope.status === 'success') settle('pass');
        else settle('error', envelope.message || `status ${envelope.status}`);
      } else if (message.type === 'run-error') {
        settle('error', message.error);
      }
    };
    worker.onerror = (event) => {
      settle('error', event.message || 'worker crashed');
    };

    worker.postMessage({ type: 'run-snippet', runId, code: PROBE_CODE });
  });
}

async function probePhase(worker) {
  for (let attempt = 1; attempt <= PROBE_ATTEMPTS; attempt++) {
    const outcome = await probeOnce(worker);
    if (outcome === 'pass') return { ok: true };
    if (outcome === 'error') return { ok: false, reason: 'probe-error' };
    // 'timeout' → retry immediately on the same worker: a truly wedged
    // runtime blocks the message loop, so the retry times out too — a slow
    // device gets a second chance, a broken runtime doesn't slip through.
  }
  return { ok: false, reason: 'probe-timeout' };
}

/**
 * Boot the worker if it isn't already up and prove it can execute Python.
 * Resolves true only after the health probe passes, false when the runner
 * is (or becomes) failed. Safe to call repeatedly — the Tutorial page calls
 * it on mount to hide the boot latency.
 */
export function ensureRunner() {
  if (!isPyodideEnabled()) return Promise.resolve(false);
  if (runner.state === 'ready' || runner.state === 'running') {
    return Promise.resolve(true);
  }
  if (runner.state === 'failed') return Promise.resolve(false);
  // Covers booting AND probing: the boot promise settles only after the
  // probe does, so concurrent callers all await the full sequence.
  if (runner.bootPromise) return runner.bootPromise;

  setState('booting');
  runner.bootPromise = (async () => {
    const worker = spawnWorker();
    runner.worker = worker;

    const boot = await bootPhase(worker);
    if (!boot.ok) {
      markFailed(boot.reason);
      return false;
    }

    setState('probing');
    const probe = await probePhase(worker);
    if (!probe.ok) {
      markFailed(probe.reason);
      return false;
    }

    // Parked handlers until the first run claims the worker: a crash while
    // idle still marks the runner failed (runOnWorker replaces these).
    worker.onmessage = null;
    worker.onerror = (event) => {
      if (runner.state === 'ready') {
        markFailed(`worker-crashed: ${event.message || 'unknown'}`);
      }
    };

    setState('ready');
    return true;
  })().finally(() => {
    runner.bootPromise = null;
  });
  return runner.bootPromise;
}

/** Terminate the current worker and boot a replacement for the next run. */
function rebootWorker() {
  runner.worker?.terminate();
  runner.worker = null;
  setState('idle');
  ensureRunner();
}

function runOnWorker(payload, timeoutEnvelope) {
  const runId = runner.nextRunId++;
  setState('running');
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
        setState('ready');
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
