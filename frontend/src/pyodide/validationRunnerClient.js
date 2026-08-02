/**
 * Singleton client for in-browser (Pyodide) agent validation.
 *
 * Owns one validation.worker.js instance per page load and acts as its
 * watchdog: Pyodide has no in-run interrupt without SharedArrayBuffer (the
 * app serves no COOP/COEP headers), so a stuck run is ended by terminating
 * the worker and booting a fresh one.
 *
 * The contract with usePyodideValidationSubmit is the resolution kind:
 *   { kind: "local", envelope }   — Pyodide ran; envelope is the normalized
 *     7-key ValidationResponse (identical shape to the server executor's),
 *     including status:"error" outcomes like a crash or the watchdog
 *     timeout. Never falls back: the server would fail the same way.
 *   { kind: "fallback", reason }  — Pyodide itself couldn't run (boot
 *     failure, failed health probe, infra crash mid-run); the caller must
 *     submit through the server path with this reason so the fallback is
 *     counted server-side.
 *
 * The health probe is game-specific and heavyweight by design: it runs a
 * FULL validation of the game's own starter_code (the harness reads it off
 * the engine tree — nothing leaves the browser, nothing is saved). A
 * runtime that can't validate starter code can't be trusted with real
 * submissions. Probe results are per game (probeResults map): a starter
 * probe that *errors* fails only that game, while a probe timeout or infra
 * error marks the whole runner failed — a device too slow for starter code
 * is too slow for every game.
 *
 * State machine: idle → booting → probing → ready ⇄ running, terminal
 * `failed`. Boot, probes, and runs are all serialized on one FIFO queue so
 * a league/game switch's re-probe can never collide with an in-flight run.
 * A run failure (timeout/crash) reboots the worker, which clears
 * probeResults — a fresh worker must re-prove itself.
 *
 * UI observes the machine via getValidationRunnerStatus /
 * subscribeValidationRunnerStatus (useSyncExternalStore-compatible: the
 * snapshot object is cached and only replaced on a transition).
 */

const BOOT_TIMEOUT_MS = 30000; // engine tree for all games (cf. simulation)
const PROBE_TIMEOUT_MS = 10000; // a probe IS a full starter validation
const PROBE_ATTEMPTS = 2;
const RUN_TIMEOUT_MS = 20000; // server soft limit is 5s; Pyodide is ~3-5x

// Same phrasing as the server executor's TIMEOUT_MESSAGE
// (backend/tasks/validation_task.py) with this runtime's honest budget —
// the prefix is matched by hint_context.classify_outcome.
const TIMEOUT_MESSAGE =
  `Your agent consumes too much time - validation did not finish within ` +
  `${RUN_TIMEOUT_MS / 1000} seconds. The agent may be too slow or stuck in a loop.`;

// Build-time kill switch: set VITE_PYODIDE_VALIDATION=false to force every
// agent submission through the server path (no fallback tagging — it's not
// a fallback, it's the configured path).
export const isPyodideValidationEnabled = () =>
  import.meta.env.VITE_PYODIDE_VALIDATION !== 'false';

const timeoutEnvelope = () => ({
  status: 'error',
  message: TIMEOUT_MESSAGE,
  feedback: null,
  simulation_results: null,
  duration_ms: null,
  traceback: null,
  stdout: null,
});

const runner = {
  state: 'idle', // idle | booting | probing | ready | running | failed
  worker: null,
  failureReason: null,
  nextRunId: 1,
  // gameName -> 'pass' | 'fail'; cleared on every worker (re)boot.
  probeResults: new Map(),
  probedGame: null,
  lastGameName: null,
  // FIFO for boot, probes, and runs alike — see module docstring.
  queue: Promise.resolve(),
};

const listeners = new Set();
// Cached so getValidationRunnerStatus returns a stable reference between
// transitions — useSyncExternalStore treats a fresh object per call as an
// endless update.
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

/** Snapshot of the runner for UI (status dot). */
export function getValidationRunnerStatus() {
  if (!statusSnapshot) {
    statusSnapshot = {
      state: runner.state,
      failureReason: runner.failureReason,
      pyodideEnabled: isPyodideValidationEnabled(),
      probedGame: runner.probedGame,
      probeResults: Object.fromEntries(runner.probeResults),
    };
  }
  return statusSnapshot;
}

/** Listen for state transitions. Returns an unsubscribe function. */
export function subscribeValidationRunnerStatus(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function spawnWorker() {
  return new Worker(new URL('./validation.worker.js', import.meta.url), {
    type: 'module',
  });
}

function markFailed(reason) {
  // Reason first so the notify inside setState publishes a coherent snapshot.
  runner.failureReason = reason;
  setState('failed');
  runner.worker?.terminate();
  runner.worker = null;
  console.warn(`Pyodide validation runner unavailable: ${reason}`);
}

/** The tagged reason a submission should carry when this runner can't run. */
function fallbackReason(gameName) {
  if (runner.failureReason) return runner.failureReason;
  if (runner.probeResults.get(gameName) === 'fail') {
    return `probe-starter-failed:${gameName}`;
  }
  return 'runner-unavailable';
}

/**
 * Wait for the worker to finish loading Pyodide, the engine tree, and the
 * harness. Resolves { ok: true } or { ok: false, reason }; never rejects.
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
 * One health-probe attempt: full starter-code validation for gameName under
 * PROBE_TIMEOUT_MS. Resolves 'pass' | 'starter-fail' | 'timeout' | 'error'.
 * Uses the shared runId counter so a stale probe result can never collide
 * with a later run (and vice versa — the runId filters discard strays).
 */
function probeOnce(worker, gameName) {
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
      // The reason sent to telemetry stays a bounded token; the underlying
      // detail is only logged.
      if (detail) console.warn(`Pyodide validation probe failed: ${detail}`);
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
        else settle('starter-fail', envelope.message || `status ${envelope.status}`);
      } else if (message.type === 'run-error') {
        settle('error', message.error);
      }
    };
    worker.onerror = (event) => {
      settle('error', event.message || 'worker crashed');
    };

    worker.postMessage({ type: 'probe-validation', runId, gameName });
  });
}

async function probePhase(worker, gameName) {
  for (let attempt = 1; attempt <= PROBE_ATTEMPTS; attempt++) {
    const outcome = await probeOnce(worker, gameName);
    if (outcome === 'pass') return { ok: true };
    // The runtime executed the probe and the starter code failed: a
    // deterministic, game-local outcome — no retry, runner stays alive.
    if (outcome === 'starter-fail') return { ok: false, gameOnly: true };
    if (outcome === 'error') return { ok: false, reason: 'probe-error' };
    // 'timeout' → retry immediately on the same worker: a truly wedged
    // runtime blocks the message loop, so the retry times out too — a slow
    // device gets a second chance, a broken runtime doesn't slip through.
  }
  return { ok: false, reason: 'probe-timeout' };
}

/**
 * Queue-internal: boot if needed, then make sure gameName's starter probe
 * has passed. Resolves true when the runner is proven for this game. Must
 * only run inside the FIFO queue.
 */
async function ensureReadyForGame(gameName) {
  if (runner.state === 'failed') return false;
  if (runner.probeResults.get(gameName) === 'fail') return false;

  if (runner.state !== 'ready' && runner.state !== 'running') {
    setState('booting');
    // A fresh worker must re-prove itself for every game.
    runner.probeResults.clear();
    runner.probedGame = null;
    const worker = spawnWorker();
    runner.worker = worker;
    const boot = await bootPhase(worker);
    if (!boot.ok) {
      markFailed(boot.reason);
      return false;
    }
  }

  if (runner.probeResults.get(gameName) !== 'pass') {
    setState('probing');
    const probe = await probePhase(runner.worker, gameName);
    if (!probe.ok) {
      if (probe.gameOnly) {
        runner.probeResults.set(gameName, 'fail');
        setState('ready'); // runner is healthy; this game routes to the server
        notify();
        return false;
      }
      markFailed(probe.reason);
      return false;
    }
    runner.probeResults.set(gameName, 'pass');
    runner.probedGame = gameName;
  }

  // Parked handlers until the next run claims the worker: a crash while
  // idle still marks the runner failed (runOnWorker replaces these).
  runner.worker.onmessage = null;
  runner.worker.onerror = (event) => {
    if (runner.state === 'ready') {
      markFailed(`worker-crashed: ${event.message || 'unknown'}`);
    }
  };

  setState('ready');
  notify();
  return true;
}

/**
 * Boot the worker if needed and prove it can validate this game's starter
 * code. Resolves true only after the probe passes. Safe to call repeatedly —
 * the submission page calls it on mount (and on game change) to hide the
 * boot+probe latency.
 */
export function ensureValidationRunner(gameName) {
  if (!isPyodideValidationEnabled() || !gameName) {
    return Promise.resolve(false);
  }
  runner.lastGameName = gameName;
  if (runner.state === 'failed') return Promise.resolve(false);
  if (runner.probeResults.get(gameName) === 'fail') {
    return Promise.resolve(false);
  }
  if (
    (runner.state === 'ready' || runner.state === 'running') &&
    runner.probeResults.get(gameName) === 'pass'
  ) {
    return Promise.resolve(true);
  }
  const task = runner.queue.then(() => ensureReadyForGame(gameName));
  runner.queue = task.catch(() => {});
  return task;
}

/** Terminate the current worker and re-warm for the last game used. */
function rebootWorker() {
  runner.worker?.terminate();
  runner.worker = null;
  runner.probeResults.clear();
  runner.probedGame = null;
  setState('idle');
  if (runner.lastGameName) ensureValidationRunner(runner.lastGameName);
}

function runOnWorker(payload) {
  const runId = runner.nextRunId++;
  setState('running');
  const worker = runner.worker;

  return new Promise((resolve) => {
    let settled = false;

    const runTimer = setTimeout(() => {
      if (settled) return;
      settled = true;
      // Agent stuck in a loop: a local outcome, not a fallback — the server
      // would time the same code out too (at its own 5s budget).
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

/**
 * Validate one agent submission in the browser.
 * Resolves { kind: "local", envelope } or { kind: "fallback", reason } —
 * see the module docstring. Runs are serialized FIFO behind any in-flight
 * boot, probe, or run.
 */
export function runValidation({ gameName, code, teamName }) {
  if (!isPyodideValidationEnabled() || !gameName) {
    return Promise.resolve({ kind: 'fallback', reason: 'runner-unavailable' });
  }
  runner.lastGameName = gameName;
  const task = runner.queue.then(async () => {
    const ready = await ensureReadyForGame(gameName);
    if (!ready) {
      return { kind: 'fallback', reason: fallbackReason(gameName) };
    }
    return runOnWorker({ type: 'run-validation', gameName, code, teamName });
  });
  // Keep the queue alive even if a task rejects unexpectedly.
  runner.queue = task.catch(() => {});
  return task;
}
