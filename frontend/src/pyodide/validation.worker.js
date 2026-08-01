/**
 * Web Worker hosting the Pyodide runtime for agent validation.
 *
 * Owned by validationRunnerClient.js, which is also the watchdog: this worker
 * has no timeout handling of its own — a stuck run (e.g. an agent looping
 * forever) is ended by the client terminating the whole worker.
 *
 * Boot writes ALL game-engine copies (frontend/src/pyodide/games/) onto
 * Pyodide's filesystem under /validate/backend/games/... and puts /validate
 * on sys.path, so the engine's own `backend.games.<game>` imports — and
 * add_player's `games.<g>.player` → `backend.games.<g>.player` rewrite of
 * student code — resolve exactly as they do server-side. Unlike the
 * simulation worker (which writes only the simulation-ready subset), every
 * game in GAME_ENGINE_FILES is written: validation is in-browser for all of
 * them. backend/config.py is generated here (the engine imports ROOT_DIR and
 * GAMES from it; the real config drags in secrets/DB settings that don't
 * exist in the browser).
 *
 * Pyodide is self-hosted from /pyodide/ (copied out of the npm package by
 * vite.config.js) so nothing here touches a CDN.
 *
 * Protocol (all messages carry plain JSON-able values, never proxies;
 * result payloads cross as JSON strings serialized inside Python). A probe
 * is just a run whose code the harness chooses itself (the game's
 * starter_code), so both answer with the same `result` message:
 *   in:  { type: "init" }
 *   in:  { type: "run-validation", runId, gameName, code, teamName }
 *   in:  { type: "probe-validation", runId, gameName }
 *   out: { type: "ready" }
 *   out: { type: "init-error", error }
 *   out: { type: "result", runId, resultJson } // 7-key validation envelope
 *   out: { type: "run-error", runId, error }   // JS-level infra failure
 */
import harnessSource from './validation_harness.py?raw';
import { SHARED_FILES, GAME_ENGINE_FILES } from './games/index.js';

const VALIDATION_ROOT = '/validate';

let bridge = null; // { runValidationJson, probeValidationJson }

function writeEngineTree(pyodide) {
  const files = { ...SHARED_FILES };
  for (const game of Object.values(GAME_ENGINE_FILES)) {
    Object.assign(files, game.files);
  }

  const dirs = new Set();
  for (const path of Object.keys(files)) {
    const parts = path.split('/').slice(0, -1);
    for (let i = 1; i <= parts.length; i++) {
      dirs.add(`${VALIDATION_ROOT}/${parts.slice(0, i).join('/')}`);
    }
  }
  for (const dir of dirs) {
    pyodide.FS.mkdirTree(dir);
    // Every package level needs an __init__.py for the imports to resolve.
    pyodide.FS.writeFile(`${dir}/__init__.py`, '');
  }
  for (const [path, source] of Object.entries(files)) {
    pyodide.FS.writeFile(`${VALIDATION_ROOT}/${path}`, source);
  }

  // The engine imports ROOT_DIR and GAMES from backend.config; the real
  // config needs env/secrets that don't exist in the browser.
  const gameNames = Object.keys(GAME_ENGINE_FILES)
    .map((name) => JSON.stringify(name))
    .join(', ');
  pyodide.FS.writeFile(
    `${VALIDATION_ROOT}/backend/config.py`,
    `ROOT_DIR = "${VALIDATION_ROOT}/backend"\nGAMES = [${gameNames}]\n`
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
  pyodide.runPython(
    `import sys; sys.path.insert(0, ${JSON.stringify(VALIDATION_ROOT)})`
  );
  await pyodide.runPythonAsync(harnessSource);
  bridge = {
    runValidationJson: pyodide.globals.get('run_validation_json'),
    probeValidationJson: pyodide.globals.get('probe_validation_json'),
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
    if (message.type === 'run-validation') {
      const resultJson = bridge.runValidationJson(
        message.gameName,
        message.code,
        message.teamName
      );
      self.postMessage({ type: 'result', runId, resultJson });
    } else if (message.type === 'probe-validation') {
      const resultJson = bridge.probeValidationJson(message.gameName);
      self.postMessage({ type: 'result', runId, resultJson });
    }
  } catch (error) {
    self.postMessage({ type: 'run-error', runId, error: String(error) });
  }
};
