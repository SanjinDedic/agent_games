// src/AgentGames/Shared/hooks/usePyodideExerciseSubmit.js
import { useCallback, useState } from 'react';
import { useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import {
  isPyodideEnabled,
  runExercise,
} from '../../../pyodide/exerciseRunnerClient';
import { runOnLambdaDirect } from '../../../utils/lambdaFallback';
import { selectToken } from '../../../slices/authSlice';
import useTutorialAPI from './useTutorialAPI';

const RUNNER_UNAVAILABLE = {
  success: false,
  error: 'Code runner unavailable',
  hint: null,
  hint_available: false,
  hint_cancelled: false,
};

/**
 * Pyodide-first submit for one exercise. The server never executes exercise
 * code — when Pyodide can't run, students go straight to the fallback
 * Lambda's Function URL; previews (admin/institution) are Pyodide-only.
 *
 * Returns { submitCode, isLoading } where submitCode has the exact contract
 * useSubmissionWorkspace expects, so the workspace and results components
 * need no changes. The paths:
 *
 * 1. Pyodide ran (any outcome, including student-code errors/timeouts):
 *    - student: persist via /tutorial/submit-exercise-result (server stamps
 *      rows "source": "pyodide" and owns the 400/429 contract);
 *    - preview: build the result locally, zero network.
 * 2. Pyodide couldn't run (or VITE_PYODIDE_EXERCISES=false), student: call
 *    the fallback Lambda's Function URL directly, then persist the envelope
 *    tagged execution_source="pyodide_fallback" — the submission doubles as
 *    the telemetry beacon. If the direct call fails too, the run surfaces as
 *    "code runner unavailable" — there is no server retry.
 * 3. Pyodide couldn't run, preview: error. Preview surfaces never use the
 *    Lambda fallback.
 */
const usePyodideExerciseSubmit = ({ exercise, preview = false }) => {
  const { submitExerciseResult, isLoading: isApiLoading } = useTutorialAPI();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);
  const [isRunningLocally, setIsRunningLocally] = useState(false);

  const submitCode = useCallback(
    async (code) => {
      if (!code || code.trim() === '') {
        toast.error('Please enter some code before submitting');
        return { success: false, error: 'Empty code submission' };
      }

      let envelope = null;
      let resultTags = {};
      let fallbackReason = null;

      if (!isPyodideEnabled()) {
        // Kill-switch build: no local runner at all.
        fallbackReason = 'pyodide-disabled';
      } else {
        setIsRunningLocally(true);
        let run;
        try {
          run = await runExercise({
            code,
            entryFunction: exercise.entry_function,
            testCode: exercise.test_code,
          });
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
        // Pyodide couldn't run. Previews stay Pyodide-only; students go
        // straight to the Lambda's Function URL.
        if (preview) {
          toast.error(
            'Could not run your code — the code runner is unavailable.'
          );
          return RUNNER_UNAVAILABLE;
        }
        setIsRunningLocally(true);
        let direct;
        try {
          direct = await runOnLambdaDirect(
            {
              kind: 'exercise',
              code,
              entry_function: exercise.entry_function,
              test_code: exercise.test_code,
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

      if (!preview) {
        const result = await submitExerciseResult(
          exercise.id, code, envelope, resultTags
        );
        if (!result.networkError) {
          return result;
        }
        // The run itself succeeded; show it, flag that it wasn't saved, and
        // never re-run (double execution).
        toast.warn('Result shown but could not be saved');
      }

      if (envelope.status === 'error') {
        toast.error(envelope.message || 'Exercise run failed');
        return {
          success: false,
          error: envelope.message,
          stdout: envelope.stdout,
          hint: null,
          hint_available: false,
          hint_cancelled: false,
        };
      }
      return {
        success: true,
        output: {
          passed: envelope.passed,
          test_results: envelope.test_results,
          stdout: envelope.stdout,
          duration_ms: envelope.duration_ms,
        },
        feedback: null,
        hint: null,
        hint_available: false,
        hint_cancelled: false,
      };
    },
    [exercise, preview, submitExerciseResult, apiUrl, accessToken]
  );

  return { submitCode, isLoading: isRunningLocally || isApiLoading };
};

export default usePyodideExerciseSubmit;
