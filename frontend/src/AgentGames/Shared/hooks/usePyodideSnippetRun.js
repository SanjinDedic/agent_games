// src/AgentGames/Shared/hooks/usePyodideSnippetRun.js
import { useCallback } from 'react';
import {
  isPyodideEnabled,
  runSnippet as runSnippetLocally,
} from '../../../pyodide/exerciseRunnerClient';
import useLessonAPI from './useLessonAPI';

/**
 * Pyodide-first run for one lesson snippet, with automatic server fallback.
 *
 * Returns { runSnippet } with the exact { success, data | error } contract
 * RunnableCodeBlock already consumes from useLessonAPI.runSnippet, so the
 * block's rendering needs no changes. The paths:
 *
 * 1. Kill switch off (VITE_PYODIDE_EXERCISES=false): the pre-existing
 *    server run, untagged.
 * 2. Pyodide ran (any outcome, including tracebacks and the watchdog
 *    timeout): the envelope is the result — zero network, nothing stored.
 * 3. Pyodide itself couldn't run: run through the server tagged
 *    execution_source="pyodide_fallback" so it is logged and counted.
 */
const usePyodideSnippetRun = () => {
  const { runSnippet: runSnippetOnServer } = useLessonAPI();

  const runSnippet = useCallback(
    async (code) => {
      if (!isPyodideEnabled()) {
        return runSnippetOnServer(code);
      }

      // Mirrors the server's 422 for blank code — exec of "" would
      // otherwise "succeed" silently with no output.
      if (!code || code.trim() === '') {
        return { success: false, error: 'Code cannot be empty' };
      }

      const run = await runSnippetLocally({ code });
      if (run.kind === 'fallback') {
        return runSnippetOnServer(code, {
          executionSource: 'pyodide_fallback',
          fallbackReason: run.reason,
        });
      }
      return { success: true, data: run.envelope };
    },
    [runSnippetOnServer]
  );

  return { runSnippet };
};

export default usePyodideSnippetRun;
