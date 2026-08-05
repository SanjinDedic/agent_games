// src/AgentGames/Shared/hooks/usePyodideSnippetRun.js
import { useCallback } from 'react';
import { useSelector } from 'react-redux';
import {
  isPyodideEnabled,
  runSnippet as runSnippetLocally,
} from '../../../pyodide/exerciseRunnerClient';
import { runOnLambdaDirect } from '../../../utils/lambdaFallback';
import { selectToken } from '../../../slices/authSlice';
import useLessonAPI from './useLessonAPI';

const RUNNER_UNAVAILABLE = {
  success: false,
  error: 'The code runner is unavailable. Please try again.',
};

/**
 * Pyodide-first run for one lesson snippet. The server never executes
 * snippet code — when Pyodide can't run, student pages go straight to the
 * fallback Lambda's Function URL (plus a fire-and-forget telemetry beacon);
 * admin previews ({ preview: true }, threaded from AdminLessons) are
 * Pyodide-only and error out instead.
 *
 * Returns { runSnippet } with the exact { success, data | error } contract
 * RunnableCodeBlock consumes, so the block's rendering needs no changes.
 */
const usePyodideSnippetRun = ({ preview = false } = {}) => {
  const { sendSnippetFallbackBeacon } = useLessonAPI();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);

  const runSnippet = useCallback(
    async (code) => {
      // Exec of "" would otherwise "succeed" silently with no output.
      if (!code || code.trim() === '') {
        return { success: false, error: 'Code cannot be empty' };
      }

      let fallbackReason = null;
      if (!isPyodideEnabled()) {
        // Kill-switch build: no local runner at all.
        fallbackReason = 'pyodide-disabled';
      } else {
        const run = await runSnippetLocally({ code });
        if (run.kind !== 'fallback') {
          return { success: true, data: run.envelope };
        }
        fallbackReason = run.reason;
      }

      if (preview) {
        return RUNNER_UNAVAILABLE;
      }
      const direct = await runOnLambdaDirect(
        { kind: 'snippet', code },
        { apiUrl, accessToken }
      );
      if (!direct.ok) {
        return RUNNER_UNAVAILABLE;
      }
      sendSnippetFallbackBeacon(fallbackReason);
      return { success: true, data: direct.envelope };
    },
    [preview, sendSnippetFallbackBeacon, apiUrl, accessToken]
  );

  return { runSnippet };
};

export default usePyodideSnippetRun;
