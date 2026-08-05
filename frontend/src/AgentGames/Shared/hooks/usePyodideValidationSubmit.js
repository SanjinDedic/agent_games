// src/AgentGames/Shared/hooks/usePyodideValidationSubmit.js
import { useCallback, useState } from 'react';
import { useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import {
  isPyodideValidationEnabled,
  runValidation,
} from '../../../pyodide/validationRunnerClient';
import { isValidationSupported } from '../../../pyodide/games/index.js';
import { runOnLambdaDirect } from '../../../utils/lambdaFallback';
import { selectToken } from '../../../slices/authSlice';
import useSubmissionAPI from './useSubmissionAPI';

// Failed local runs are persisted too (metadata-only row, no code) so the
// rate limit, teacher analytics, and hint accounting keep working exactly
// as before. Flip to false to keep failures fully local.
const PERSIST_LOCAL_FAILURES = true;

const RUNNER_UNAVAILABLE = {
  success: false,
  error: 'Code runner unavailable',
  hint: null,
  hint_available: false,
  hint_cancelled: false,
};

/**
 * Pyodide-first agent submission. The server never executes agent code —
 * every envelope is produced in the browser and persisted via
 * /user/submit-agent-result.
 *
 * Returns { submitCode, isLoading } where submitCode has the exact contract
 * useSubmissionWorkspace expects, so the workspace and feedback components
 * need no changes. The paths:
 *
 * 1. Pyodide ran (any outcome, including agent errors and the local timeout
 *    envelope): persist the envelope — the server re-runs the AST gate,
 *    applies the shared rate limit, and owns the 400/429 contract.
 * 2. Pyodide couldn't run (boot/probe/infra failure), the kill switch is off
 *    (VITE_PYODIDE_VALIDATION=false, reason "pyodide-disabled"), or the
 *    league's game isn't in the browser engine registry: call the validation
 *    Lambda's Function URL directly, then persist the envelope tagged
 *    execution_source="pyodide_fallback" — the submission doubles as the
 *    telemetry beacon. If the direct call fails too, the run surfaces as
 *    "code runner unavailable" — there is no server retry.
 * 3. Hint requested: Pyodide-only. The local envelope rides the same persist
 *    with generate_hint=true and the server builds the hint from it; when
 *    Pyodide can't run the hint request fails gracefully — the Lambda is
 *    never called for a hint.
 */
const usePyodideValidationSubmit = ({ gameName, teamName }) => {
  const { submitAgentResult, isLoading: isApiLoading } = useSubmissionAPI();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);
  const [isRunningLocally, setIsRunningLocally] = useState(false);

  const submitCode = useCallback(
    async (code, { generateHint = false } = {}) => {
      if (!code || code.trim() === '') {
        toast.error('Please enter some code before submitting');
        return { success: false, error: 'Empty code submission' };
      }

      let envelope = null;
      let resultTags = {};
      let fallbackReason = null;

      const pyodideUsable =
        isPyodideValidationEnabled() &&
        Boolean(gameName) &&
        isValidationSupported(gameName);

      if (!pyodideUsable) {
        fallbackReason = !isPyodideValidationEnabled()
          ? 'pyodide-disabled'
          : `game-unsupported:${gameName}`;
      } else {
        setIsRunningLocally(true);
        let run;
        try {
          run = await runValidation({ gameName, code, teamName });
        } finally {
          setIsRunningLocally(false);
        }
        if (run.kind === 'fallback') {
          fallbackReason = run.reason;
        } else {
          envelope = run.envelope;
        }
      }

      if (!envelope) {
        // Pyodide couldn't run. Hints are Pyodide-only: the Lambda is never
        // called for a hint request.
        if (generateHint) {
          toast.error(
            'AI hints need the in-browser runner — it is unavailable right now.'
          );
          return RUNNER_UNAVAILABLE;
        }
        setIsRunningLocally(true);
        let direct;
        try {
          direct = await runOnLambdaDirect(
            {
              kind: 'validation',
              code,
              game_name: gameName,
              team_name: teamName,
            },
            { apiUrl, accessToken }
          );
        } finally {
          setIsRunningLocally(false);
        }
        if (!direct.ok) {
          toast.error(
            'Could not run your code — the code runner is unavailable. ' +
              'Please try again.'
          );
          return RUNNER_UNAVAILABLE;
        }
        envelope = direct.envelope;
        resultTags = {
          executionSource: 'pyodide_fallback',
          fallbackReason,
        };
      }

      if (
        envelope.status === 'success' ||
        PERSIST_LOCAL_FAILURES ||
        generateHint
      ) {
        const result = await submitAgentResult(code, envelope, {
          ...resultTags,
          generateHint,
        });
        if (!result.networkError) {
          return result;
        }
        // The run itself finished in the browser; show it, flag that it
        // wasn't saved (a requested hint is lost too), and never re-run.
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
    [gameName, teamName, submitAgentResult, apiUrl, accessToken]
  );

  return { submitCode, isLoading: isRunningLocally || isApiLoading };
};

export default usePyodideValidationSubmit;
