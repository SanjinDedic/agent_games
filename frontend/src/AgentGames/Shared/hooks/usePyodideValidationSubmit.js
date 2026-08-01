// src/AgentGames/Shared/hooks/usePyodideValidationSubmit.js
import { useCallback, useState } from 'react';
import { toast } from 'react-toastify';
import {
  isPyodideValidationEnabled,
  runValidation,
} from '../../../pyodide/validationRunnerClient';
import { isValidationSupported } from '../../../pyodide/games/index.js';
import useSubmissionAPI from './useSubmissionAPI';

// Failed local runs are persisted too (metadata-only row, no code) so the
// rate limit, teacher analytics, and hint accounting keep working exactly
// as on the Celery path. Flip to false to keep failures fully local.
const PERSIST_LOCAL_FAILURES = true;

/**
 * Pyodide-first agent submission, with automatic Celery fallback.
 *
 * Returns { submitCode, isLoading } where submitCode has the exact contract
 * useSubmissionWorkspace expects from useSubmissionAPI.submitCode, so the
 * workspace and feedback components need no changes. The paths:
 *
 * 1. Hint requested: straight to the Celery path, untagged — hint
 *    generation needs the server anyway, and its validation run feeds the
 *    hint context.
 * 2. Kill switch off (VITE_PYODIDE_VALIDATION=false) or the league's game
 *    isn't in the browser engine registry: the pre-existing Celery
 *    submission, untagged.
 * 3. Pyodide ran (any outcome, including agent errors/timeouts): persist
 *    via /user/submit-agent-result — the server re-runs the AST gate,
 *    applies the shared rate limit, and owns the 400/429 contract.
 * 4. Pyodide itself couldn't run (boot/probe/infra failure): submit through
 *    Celery tagged execution_source="pyodide_fallback" so the server logs
 *    and counts it (validation: reason prefix).
 */
const usePyodideValidationSubmit = ({ gameName, teamName }) => {
  const {
    submitCode: submitViaServer,
    submitAgentResult,
    isLoading: isApiLoading,
  } = useSubmissionAPI();
  const [isRunningLocally, setIsRunningLocally] = useState(false);

  const submitCode = useCallback(
    async (code, { generateHint = false } = {}) => {
      if (generateHint) {
        return submitViaServer(code, { generateHint: true });
      }
      if (
        !isPyodideValidationEnabled() ||
        !gameName ||
        !isValidationSupported(gameName)
      ) {
        return submitViaServer(code);
      }

      if (!code || code.trim() === '') {
        toast.error('Please enter some code before submitting');
        return { success: false, error: 'Empty code submission' };
      }

      setIsRunningLocally(true);
      let run;
      try {
        run = await runValidation({ gameName, code, teamName });
      } finally {
        setIsRunningLocally(false);
      }

      if (run.kind === 'fallback') {
        return submitViaServer(code, {
          executionSource: 'pyodide_fallback',
          fallbackReason: run.reason,
        });
      }

      const envelope = run.envelope;

      if (envelope.status === 'success' || PERSIST_LOCAL_FAILURES) {
        const result = await submitAgentResult(code, envelope);
        if (!result.networkError) {
          return result;
        }
        // The run itself finished locally; show it, flag that it wasn't
        // saved, and never re-run through Celery (double execution).
        toast.warn('Result shown but could not be saved');
      }

      if (envelope.status === 'error') {
        toast.error(envelope.message || 'Code validation failed');
        return {
          success: false,
          error: envelope.message,
          hint: null,
          hint_available: false,
          hint_cancelled: false,
        };
      }
      return {
        success: true,
        output: envelope.simulation_results,
        feedback: envelope.feedback,
        hint: null,
        hint_available: false,
        hint_cancelled: false,
      };
    },
    [gameName, teamName, submitViaServer, submitAgentResult]
  );

  return { submitCode, isLoading: isRunningLocally || isApiLoading };
};

export default usePyodideValidationSubmit;
