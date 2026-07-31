// src/AgentGames/Shared/hooks/usePyodideExerciseSubmit.js
import { useCallback, useState } from 'react';
import { toast } from 'react-toastify';
import {
  isPyodideEnabled,
  runExercise,
} from '../../../pyodide/exerciseRunnerClient';
import useTutorialAPI from './useTutorialAPI';

/**
 * Pyodide-first submit for one exercise, with automatic Celery fallback.
 *
 * Returns { submitCode, isLoading } where submitCode has the exact contract
 * useSubmissionWorkspace expects from useTutorialAPI.submitExercise, so the
 * workspace and results components need no changes. The paths:
 *
 * 1. Kill switch off (VITE_PYODIDE_EXERCISES=false): the pre-existing
 *    Celery submission, untagged.
 * 2. Pyodide ran (any outcome, including student-code errors/timeouts):
 *    - student: persist via /tutorial/submit-exercise-result (server stamps
 *      rows "source": "pyodide" and owns the 400/429 contract);
 *    - preview: build the result locally, zero network.
 * 3. Pyodide itself couldn't run: submit through Celery tagged
 *    execution_source="pyodide_fallback" so the server logs and counts it.
 */
const usePyodideExerciseSubmit = ({ exercise, preview = false }) => {
  const { submitExercise, submitExerciseResult, isLoading: isApiLoading } =
    useTutorialAPI();
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

      if (run.kind === 'fallback') {
        return submitExercise(exercise.id, code, {
          preview,
          executionSource: 'pyodide_fallback',
          fallbackReason: run.reason,
        });
      }

      const envelope = run.envelope;

      if (!preview) {
        const result = await submitExerciseResult(exercise.id, code, envelope);
        if (!result.networkError) {
          return result;
        }
        // The run itself succeeded locally; show it, flag that it wasn't
        // saved, and never re-run through Celery (double execution).
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
    [exercise, preview, submitExercise, submitExerciseResult]
  );

  return { submitCode, isLoading: isRunningLocally || isApiLoading };
};

export default usePyodideExerciseSubmit;
