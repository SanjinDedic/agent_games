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

  return {
    isLoading,
    getTutorials,
    getTutorial,
    getLatestExerciseSubmission,
    getExerciseSubmissions,
    submitExercise,
  };
};

export default useTutorialAPI;
