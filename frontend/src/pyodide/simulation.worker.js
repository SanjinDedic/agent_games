/**
 * Web Worker hosting the Pyodide runtime for league simulations.
 *
 * Owned by simulationRunnerClient.js, which is also the watchdog: this worker
 * has no timeout handling of its own — a stuck run (e.g. an agent looping
 * forever) is ended by the client terminating the whole worker.
 *
 * Boot writes the game-engine copies (frontend/src/pyodide/games/) onto
 * Pyodide's filesystem under /sim/backend/games/... and puts /sim on
 * sys.path, so the engine's own `backend.games.<game>` imports — and
 * add_player's `games.<g>.player` → `backend.games.<g>.player` rewrite of
 * student code — resolve exactly as they do server-side. backend/config.py is
 * generated here (the engine imports ROOT_DIR and GAMES from it; the real
 * config drags in secrets/DB settings that don't exist in the browser).
 *
 * Pyodide is self-hosted from /pyodide/ (copied out of the npm package by
 * vite.config.js) so nothing here touches a CDN.
 *
 * Protocol (all messages carry plain JSON-able values, never proxies;
 * result payloads cross as JSON strings serialized inside Python):
 *   in:  { type: "init" }
 *   in:  { type: "setup-run", runId, gameName, submissionsJson,
 *          customRewardsJson, requestedSimulations }
 *   in:  { type: "run-chunk", runId, count }
 *   in:  { type: "finalize", runId, capped }
 *   out: { type: "ready" }
 *   out: { type: "init-error", error }
 *   out: { type: "setup-done", runId, resultJson }  // ok or error envelope
 *   out: { type: "chunk-done", runId, resultJson }  // ok or error envelope
 *   out: { type: "run-complete", runId, resultJson } // full success envelope
 *   out: { type: "worker-error", runId, error }     // JS-level infra failure
 */
import harnessSource from './simulation_harness.py?raw';
import { SHARED_FILES, SIMULATION_GAMES } from './games/index.js';

const SIM_ROOT = '/sim';

let bridge = null; // { setupRunJson, runChunkJson, finalizeJson }

function writeEngineTree(pyodide) {
  const files = { ...SHARED_FILES };
  for (const game of Object.values(SIMULATION_GAMES)) {
    Object.assign(files, game.files);
  }

  const dirs = new Set();
  for (const path of Object.keys(files)) {
    const parts = path.split('/').slice(0, -1);
    for (let i = 1; i <= parts.length; i++) {
      dirs.add(`${SIM_ROOT}/${parts.slice(0, i).join('/')}`);
    }
  }
  for (const dir of dirs) {
    pyodide.FS.mkdirTree(dir);
    // Every package level needs an __init__.py for the imports to resolve.
    pyodide.FS.writeFile(`${dir}/__init__.py`, '');
  }
  for (const [path, source] of Object.entries(files)) {
    pyodide.FS.writeFile(`${SIM_ROOT}/${path}`, source);
  }

  // The engine imports ROOT_DIR and GAMES from backend.config; the real
  // config needs env/secrets that don't exist in the browser.
  const gameNames = Object.keys(SIMULATION_GAMES)
    .map((name) => JSON.stringify(name))
    .join(', ');
  pyodide.FS.writeFile(
    `${SIM_ROOT}/backend/config.py`,
    `ROOT_DIR = "${SIM_ROOT}/backend"\nGAMES = [${gameNames}]\n`
  );
}

async function boot() {
  const base = self.location.origin;
  const url = new URL('/pyodide/pyodide.mjs', base).href;
  const { loadPyodide } = await import(/* @vite-ignore */ url);
  const pyodide = await loadPyodide({
    indexURL: new URL('/pyodide/', base).href,
  });
  writeEngineTree(pyodide);
  pyodide.runPython(`import sys; sys.path.insert(0, ${JSON.stringify(SIM_ROOT)})`);
  await pyodide.runPythonAsync(harnessSource);
  bridge = {
    setupRunJson: pyodide.globals.get('setup_run_json'),
    runChunkJson: pyodide.globals.get('run_chunk_json'),
    finalizeJson: pyodide.globals.get('finalize_json'),
  };
}

self.onmessage = async (event) => {
  const message = event.data;

  if (message.type === 'init') {
    try {
      await boot();
      self.postMessage({ type: 'ready' });
    } catch (error) {
      self.postMessage({ type: 'init-error', error: String(error) });
    }
    return;
  }

  const { runId } = message;
  try {
    if (message.type === 'setup-run') {
      const resultJson = bridge.setupRunJson(
        message.gameName,
        message.submissionsJson ?? '',
        message.customRewardsJson ?? '',
        message.requestedSimulations
      );
      self.postMessage({ type: 'setup-done', runId, resultJson });
    } else if (message.type === 'run-chunk') {
      const resultJson = bridge.runChunkJson(message.count);
      self.postMessage({ type: 'chunk-done', runId, resultJson });
    } else if (message.type === 'finalize') {
      const resultJson = bridge.finalizeJson(message.capped);
      self.postMessage({ type: 'run-complete', runId, resultJson });
    }
  } catch (error) {
    self.postMessage({ type: 'worker-error', runId, error: String(error) });
  }
};
