// src/AgentGames/Shared/hooks/usePyodideSnippetRun.js
import { useCallback } from 'react';
import { useSelector } from 'react-redux';
import {
  isPyodideEnabled,
  runSnippet as runSnippetLocally,
} from '../../../pyodide/exerciseRunnerClient';
import {
  isLambdaDirectEnabled,
  runOnLambdaDirect,
} from '../../../utils/lambdaFallback';
import { selectToken } from '../../../slices/authSlice';
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
 * 3. Pyodide itself couldn't run and VITE_EXERCISE_LAMBDA_URL is set: call
 *    the fallback Lambda's Function URL directly, and fire the telemetry
 *    beacon at the API (nothing to persist for snippets).
 * 4. Direct path unavailable or failed: run through the server tagged
 *    execution_source="pyodide_fallback" as before.
 */
const usePyodideSnippetRun = () => {
  const { runSnippet: runSnippetOnServer, sendSnippetFallbackBeacon } =
    useLessonAPI();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);

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
        if (isLambdaDirectEnabled()) {
          const direct = await runOnLambdaDirect(
            { kind: 'snippet', code },
            { apiUrl, accessToken }
          );
          if (direct.ok) {
            sendSnippetFallbackBeacon(run.reason);
            return { success: true, data: direct.envelope };
          }
        }
        return runSnippetOnServer(code, {
          executionSource: 'pyodide_fallback',
          fallbackReason: run.reason,
        });
      }
      return { success: true, data: run.envelope };
    },
    [runSnippetOnServer, sendSnippetFallbackBeacon, apiUrl, accessToken]
  );

  return { runSnippet };
};

export default usePyodideSnippetRun;
