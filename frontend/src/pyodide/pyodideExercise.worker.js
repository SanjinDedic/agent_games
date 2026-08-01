/**
 * Web Worker hosting the Pyodide runtime for exercise runs.
 *
 * Owned by exerciseRunnerClient.js, which is also the watchdog: this worker
 * has no timeout handling of its own — a stuck run is ended by the client
 * terminating the whole worker and spawning a fresh one.
 *
 * Pyodide is self-hosted from /pyodide/ (copied out of the npm package by
 * vite.config.js) so nothing here touches a CDN. The URL is built as a
 * runtime string and imported with @vite-ignore so Vite doesn't try to
 * bundle the runtime.
 *
 * Protocol (all messages carry plain JSON-able values, never proxies):
 *   in:  { type: "init" }
 *   in:  { type: "run", runId, code, entryFunction, testCode }
 *   in:  { type: "run-snippet", runId, code }
 *   out: { type: "ready" }
 *   out: { type: "init-error", error }
 *   out: { type: "result", runId, resultJson }   // normalized envelope JSON
 *   out: { type: "run-error", runId, error }     // JS-level infra failure
 */
import harnessSource from './exercise_harness.py?raw';

let runExerciseJson = null;
let runSnippetJson = null;

async function boot() {
  const base = self.location.origin;
  const url = new URL('/pyodide/pyodide.mjs', base).href;
  const { loadPyodide } = await import(/* @vite-ignore */ url);
  const pyodide = await loadPyodide({
    indexURL: new URL('/pyodide/', base).href,
  });
  await pyodide.runPythonAsync(harnessSource);
  runExerciseJson = pyodide.globals.get('run_exercise_json');
  runSnippetJson = pyodide.globals.get('run_snippet_json');
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

  if (message.type === 'run') {
    const { runId, code, entryFunction, testCode } = message;
    try {
      // The harness serializes the envelope inside Python, so a plain JS
      // string comes back — no PyProxy crosses postMessage.
      const resultJson = runExerciseJson(
        code,
        entryFunction ?? '',
        testCode ?? null
      );
      self.postMessage({ type: 'result', runId, resultJson });
    } catch (error) {
      self.postMessage({ type: 'run-error', runId, error: String(error) });
    }
    return;
  }

  if (message.type === 'run-snippet') {
    const { runId, code } = message;
    try {
      const resultJson = runSnippetJson(code);
      self.postMessage({ type: 'result', runId, resultJson });
    } catch (error) {
      self.postMessage({ type: 'run-error', runId, error: String(error) });
    }
  }
};
