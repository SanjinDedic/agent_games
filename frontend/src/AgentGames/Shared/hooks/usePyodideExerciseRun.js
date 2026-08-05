// src/AgentGames/Shared/hooks/usePyodideExerciseRun.js
import { useCallback } from 'react';
import {
  isPyodideEnabled,
  runExercise,
} from '../../../pyodide/exerciseRunnerClient';

/**
 * Pyodide-only dry run for the admin exercise editor's Run button. Admin
 * pages never use the Lambda fallback: if Pyodide can't run, the button
 * errors instead. Matches the { success, data | error } contract the editor's
 * handleRun consumes — data is the full harness envelope, traceback included,
 * so broken test scripts still render for the person debugging them.
 */
const usePyodideExerciseRun = () => {
  return useCallback(async (code, entryFunction, testCode) => {
    if (!isPyodideEnabled()) {
      return {
        success: false,
        error: 'Pyodide is disabled in this build (VITE_PYODIDE_EXERCISES).',
      };
    }
    const run = await runExercise({ code, entryFunction, testCode });
    if (run.kind === 'fallback') {
      return {
        success: false,
        error: `Pyodide unavailable: ${run.reason}`,
      };
    }
    return { success: true, data: run.envelope };
  }, []);
};

export default usePyodideExerciseRun;
