// src/AgentGames/Shared/hooks/useTutorialAPI.js
import { useState, useCallback } from 'react';
import { useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import { authFetch } from '../../../utils/authFetch';
import { selectToken } from '../../../slices/authSlice';

/**
 * Hook for the tutorial/exercise API. The submission-shaped methods
 * (getLatestSubmission / getSubmissionHistory / submitCode) return the same
 * result shapes as useSubmissionAPI so useSubmissionWorkspace can drive an
 * exercise page unchanged.
 */
export const useTutorialAPI = () => {
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);
  const [isLoading, setIsLoading] = useState(false);

  /**
   * List all tutorials
   */
  const getTutorials = useCallback(async () => {
    try {
      const response = await authFetch(`${apiUrl}/tutorial/tutorials`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        },
      });

      const data = await response.json();

      if (response.ok && Array.isArray(data.tutorials)) {
        return { success: true, tutorials: data.tutorials };
      }
      return {
        success: false,
        error: data.detail || "Failed to load tutorials",
      };
    } catch (error) {
      console.error("Error loading tutorials:", error);
      return { success: false, error: "Network error while loading tutorials" };
    }
  }, [apiUrl, accessToken]);

  /**
   * Get one tutorial with its exercises in order
   */
  const getTutorial = useCallback(async (tutorialId) => {
    try {
      const response = await authFetch(`${apiUrl}/tutorial/tutorial/${tutorialId}`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        },
      });

      const data = await response.json();

      if (response.ok) {
        return { success: true, tutorial: data };
      }
      return {
        success: false,
        error: data.detail || "Failed to load tutorial",
      };
    } catch (error) {
      console.error("Error loading tutorial:", error);
      return { success: false, error: "Network error while loading tutorial" };
    }
  }, [apiUrl, accessToken]);

  /**
   * Get the team's attempted/passed status for each exercise in a tutorial
   */
  const getTutorialProgress = useCallback(async (tutorialId) => {
    try {
      const response = await authFetch(
        `${apiUrl}/tutorial/tutorial/${tutorialId}/progress`,
        {
          headers: {
            'Authorization': `Bearer ${accessToken}`
          },
        }
      );

      const data = await response.json();

      if (response.ok && Array.isArray(data.progress)) {
        return { success: true, progress: data.progress };
      }
      return {
        success: false,
        error: data.detail || "Failed to load tutorial progress",
      };
    } catch (error) {
      console.error("Error loading tutorial progress:", error);
      return { success: false, error: "Network error while loading progress" };
    }
  }, [apiUrl, accessToken]);

  /**
   * Get the team's latest submission for an exercise
   */
  const getLatestExerciseSubmission = useCallback(async (exerciseId) => {
    try {
      const response = await authFetch(
        `${apiUrl}/tutorial/exercise/${exerciseId}/latest-submission`,
        {
          headers: {
            'Authorization': `Bearer ${accessToken}`
          },
        }
      );

      const data = await response.json();

      if (response.ok && data.code) {
        return {
          success: true,
          hasSubmission: true,
          code: data.code,
          passed: data.passed,
        };
      }
      return { success: true, hasSubmission: false };
    } catch (error) {
      console.error("Error loading exercise submission:", error);
      return {
        success: false,
        error: "Network error while getting submission"
      };
    }
  }, [apiUrl, accessToken]);

  /**
   * Get the team's full submission history for an exercise
   */
  const getExerciseSubmissions = useCallback(async (exerciseId) => {
    try {
      const response = await authFetch(
        `${apiUrl}/tutorial/exercise/${exerciseId}/submissions`,
        {
          headers: {
            'Authorization': `Bearer ${accessToken}`
          },
        }
      );

      const data = await response.json();

      if (response.ok && Array.isArray(data.submissions)) {
        return { success: true, submissions: data.submissions };
      }
      return {
        success: false,
        error: data.detail || "Failed to load submissions",
      };
    } catch (error) {
      console.error("Error loading exercise submission history:", error);
      return {
        success: false,
        error: "Network error while loading submissions",
      };
    }
  }, [apiUrl, accessToken]);

  /**
   * Record that the student revealed one hint of an exercise.
   *
   * Fire-and-forget: this only feeds the teacher's concept mastery view, so a
   * failure must never interrupt a student who is asking for help. The server
   * ignores repeats, so the caller doesn't have to track what it already sent.
   */
  const recordHintReveal = useCallback(async (exerciseId, hintIndex) => {
    try {
      await authFetch(
        `${apiUrl}/tutorial/exercise/${exerciseId}/hint-revealed`,
        {
          method: "POST",
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`
          },
          body: JSON.stringify({ hint_index: hintIndex }),
        }
      );
    } catch (error) {
      console.error("Error recording hint reveal:", error);
    }
  }, [apiUrl, accessToken]);

  /**
   * Persist an exercise attempt the browser already ran via Pyodide.
   * `envelope` is the harness's normalized result ({ status, message,
   * passed, test_results, stdout, duration_ms, ... }). Returns the
   * workspace result shape ({ success, output | error, hint... }).
   *
   * When the envelope came from a direct Lambda Function URL call instead
   * of a local Pyodide run, executionSource="pyodide_fallback" makes this
   * submission double as the fallback-telemetry beacon.
   */
  const submitExerciseResult = useCallback(async (
    exerciseId,
    code,
    envelope,
    { executionSource = null, fallbackReason = null } = {}
  ) => {
    setIsLoading(true);
    const body = {
      exercise_id: exerciseId,
      code,
      status: envelope.status,
      message: envelope.message,
      passed: envelope.passed,
      test_results: envelope.test_results,
      stdout: envelope.stdout,
      duration_ms: envelope.duration_ms,
    };
    if (executionSource) {
      body.execution_source = executionSource;
      body.fallback_reason = fallbackReason;
    }
    try {
      const response = await authFetch(`${apiUrl}/tutorial/submit-exercise-result`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${accessToken}`,
        },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (response.ok) {
        return {
          success: true,
          output: {
            passed: data.passed,
            test_results: data.test_results,
            stdout: data.stdout,
            duration_ms: data.duration_ms,
          },
          feedback: null,
          hint: null,
          hint_available: false,
          hint_cancelled: false,
        };
      }
      toast.error(data.detail || "Error in submission");
      return {
        success: false,
        error: data.detail,
        stdout: data.stdout,
        hint: null,
        hint_available: false,
        hint_cancelled: false,
      };
    } catch (error) {
      console.error("Error persisting exercise result:", error);
      // The run itself succeeded locally; the caller decides how to surface
      // an unsaved result, so no toast here.
      return { success: false, error: "network", networkError: true };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken]);

  // ------------------------------------------------------------------
  // Admin content management (admin token required by the backend)
  // ------------------------------------------------------------------

  /**
   * Shared plumbing for the admin CRUD calls: JSON request, and a
   * { success, data | error } result.
   */
  const adminRequest = useCallback(async (path, method = 'GET', body = null) => {
    try {
      const options = {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
      };
      if (body !== null) {
        options.body = JSON.stringify(body);
      }
      const response = await authFetch(`${apiUrl}/tutorial${path}`, options);
      const data = await response.json();

      if (response.ok) {
        return { success: true, data };
      }
      // 422 validation errors arrive as a list of pydantic error objects.
      const detail = Array.isArray(data.detail)
        ? data.detail.map((err) => err.msg).join('; ')
        : data.detail;
      return { success: false, error: detail || 'Request failed' };
    } catch (error) {
      console.error(`Error calling ${method} ${path}:`, error);
      return { success: false, error: 'Network error' };
    }
  }, [apiUrl, accessToken]);

  /** Get one tutorial with full exercise definitions (incl. test scripts). */
  const getTutorialAdmin = useCallback(
    (tutorialId) => adminRequest(`/admin/tutorial/${tutorialId}`),
    [adminRequest]
  );

  const createTutorial = useCallback(
    (title, description) =>
      adminRequest('/tutorials', 'POST', { title, description }),
    [adminRequest]
  );

  const updateTutorial = useCallback(
    (tutorialId, title, description) =>
      adminRequest(`/tutorial/${tutorialId}`, 'PUT', { title, description }),
    [adminRequest]
  );

  const deleteTutorial = useCallback(
    (tutorialId) => adminRequest(`/tutorial/${tutorialId}`, 'DELETE'),
    [adminRequest]
  );

  /** exercise = { title, problem_markdown, starter_code, entry_function,
   *  test_code } */
  const createExercise = useCallback(
    (tutorialId, exercise) =>
      adminRequest(`/tutorial/${tutorialId}/exercises`, 'POST', exercise),
    [adminRequest]
  );

  const updateExercise = useCallback(
    (exerciseId, exercise) =>
      adminRequest(`/exercise/${exerciseId}`, 'PUT', exercise),
    [adminRequest]
  );

  const deleteExercise = useCallback(
    (exerciseId) => adminRequest(`/exercise/${exerciseId}`, 'DELETE'),
    [adminRequest]
  );

  /** exerciseIds: the tutorial's complete id list in the desired order. */
  const reorderExercises = useCallback(
    (tutorialId, exerciseIds) =>
      adminRequest(`/tutorial/${tutorialId}/exercises/reorder`, 'POST', {
        exercise_ids: exerciseIds,
      }),
    [adminRequest]
  );

  return {
    isLoading,
    getTutorials,
    getTutorial,
    getTutorialProgress,
    getLatestExerciseSubmission,
    getExerciseSubmissions,
    recordHintReveal,
    submitExerciseResult,
    getTutorialAdmin,
    createTutorial,
    updateTutorial,
    deleteTutorial,
    createExercise,
    updateExercise,
    deleteExercise,
    reorderExercises,
  };
};

export default useTutorialAPI;
