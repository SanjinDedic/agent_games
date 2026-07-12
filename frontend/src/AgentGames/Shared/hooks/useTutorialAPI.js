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
   * Submit exercise code and get per-test-case results.
   * Failing tests come back as a success whose output lists the failures;
   * a 400 means the code never produced test results (unsafe/crashed/timeout).
   */
  const submitExercise = useCallback(async (exerciseId, code) => {
    if (!code || code.trim() === "") {
      toast.error("Please enter some code before submitting");
      return { success: false, error: "Empty code submission" };
    }

    setIsLoading(true);

    try {
      const response = await authFetch(`${apiUrl}/tutorial/submit-exercise`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ exercise_id: exerciseId, code }),
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
        hint: null,
        hint_available: false,
        hint_cancelled: false,
      };
    } catch (error) {
      console.error("Error during exercise submission:", error);
      toast.error("Network error during submission. Please try again.");
      return { success: false, error: "Network error during submission" };
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

  /** Get one tutorial with full exercise definitions (incl. test cases). */
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

  /** exercise = { title, problem_markdown, starter_code, entry_function, test_cases } */
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
    submitExercise,
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
