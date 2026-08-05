// src/AgentGames/Shared/hooks/usePyodideExerciseSubmit.js
import { useCallback, useState } from 'react';
import { useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import {
  isPyodideEnabled,
  runExercise,
} from '../../../pyodide/exerciseRunnerClient';
import {
  isLambdaDirectEnabled,
  runOnLambdaDirect,
} from '../../../utils/lambdaFallback';
import { selectToken } from '../../../slices/authSlice';
import useTutorialAPI from './useTutorialAPI';

/**
 * Pyodide-first submit for one exercise, with automatic server fallback.
 *
 * Returns { submitCode, isLoading } where submitCode has the exact contract
 * useSubmissionWorkspace expects from useTutorialAPI.submitExercise, so the
 * workspace and results components need no changes. The paths:
 *
 * 1. Kill switch off (VITE_PYODIDE_EXERCISES=false): the pre-existing
 *    server submission, untagged.
 * 2. Pyodide ran (any outcome, including student-code errors/timeouts):
 *    - student: persist via /tutorial/submit-exercise-result (server stamps
 *      rows "source": "pyodide" and owns the 400/429 contract);
 *    - preview: build the result locally, zero network.
 * 3. Pyodide itself couldn't run and VITE_EXERCISE_LAMBDA_URL is set
 *    (students only): call the fallback Lambda's Function URL directly, then
 *    persist the envelope tagged execution_source="pyodide_fallback" — the
 *    submission doubles as the telemetry beacon. The API never runs the code.
 * 4. Direct path unavailable or failed (and previews always): submit through
 *    the server tagged execution_source="pyodide_fallback" as before.
 */
const usePyodideExerciseSubmit = ({ exercise, preview = false }) => {
  const { submitExercise, submitExerciseResult, isLoading: isApiLoading } =
    useTutorialAPI();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);
  const [isRunningLocally, setIsRunningLocally] = useState(false);

  const submitCode = useCallback(
    async (code) => {
      if (!isPyodideEnabled()) {
        return submitExercise(exercise.id, code, { preview });
      }

      if (!code || code.trim() === '') {
        toast.error('Please enter some code before submitting');
        return { success: false, error: 'Empty code submission' };
      }

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

      let envelope = null;
      let resultTags = {};
      if (run.kind === 'fallback') {
        // Previews stay on the proxied route: the persist leg below needs a
        // team token, and preview traffic is rare admin/institution use.
        if (!preview && isLambdaDirectEnabled()) {
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
          if (direct.ok) {
            envelope = direct.envelope;
            resultTags = {
              executionSource: 'pyodide_fallback',
              fallbackReason: run.reason,
            };
          }
        }
        if (!envelope) {
          return submitExercise(exercise.id, code, {
            preview,
            executionSource: 'pyodide_fallback',
            fallbackReason: run.reason,
          });
        }
      } else {
        envelope = run.envelope;
      }

      if (!preview) {
        const result = await submitExerciseResult(
          exercise.id, code, envelope, resultTags
        );
        if (!result.networkError) {
          return result;
        }
        // The run itself succeeded locally; show it, flag that it wasn't
        // saved, and never re-run on the server (double execution).
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
    [exercise, preview, submitExercise, submitExerciseResult, apiUrl, accessToken]
  );

  return { submitCode, isLoading: isRunningLocally || isApiLoading };
};

export default usePyodideExerciseSubmit;
