// src/AgentGames/Shared/hooks/useSubmissionAPI.js
import { useState, useCallback } from 'react';
import { useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import { authFetch } from '../../../utils/authFetch';
import { selectToken } from '../../../slices/authSlice';

/**
 * Hook for handling code submission-related API calls
 * @returns {Object} API methods and loading state
 */
export const useSubmissionAPI = () => {
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);
  const [isLoading, setIsLoading] = useState(false);
  
  /**
   * Get latest code submission
   */
  const getLatestSubmission = useCallback(async () => {
    try {
      const response = await authFetch(`${apiUrl}/user/get-team-submission`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        },
      });

      const data = await response.json();

      if (response.ok && data.code) {
        return {
          success: true,
          hasSubmission: true,
          code: data.code
        };
      } else {
        return {
          success: true,
          hasSubmission: false
        };
      }
    } catch (error) {
      console.error("Error loading submission:", error);
      return { 
        success: false, 
        error: "Network error while getting submission" 
      };
    }
  }, [apiUrl, accessToken]);
  
  /**
   * Get full submission history for current team
   */
  const getTeamSubmissions = useCallback(async () => {
    try {
      const response = await authFetch(`${apiUrl}/user/get-team-submissions`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        },
      });

      const data = await response.json();

      if (response.ok && Array.isArray(data.submissions)) {
        return {
          success: true,
          submissions: data.submissions,
        };
      } else {
        return {
          success: false,
          error: data.detail || "Failed to load submissions",
        };
      }
    } catch (error) {
      console.error("Error loading submission history:", error);
      return {
        success: false,
        error: "Network error while loading submissions",
      };
    }
  }, [apiUrl, accessToken]);

  /**
   * Get game instructions and starter code
   */
  const getGameInstructions = useCallback(async (gameName) => {
    try {
      const response = await fetch(`${apiUrl}/user/get-game-instructions`, {
        method: "POST",
        headers: { 
          'Content-Type': 'application/json' 
        },
        body: JSON.stringify({ game_name: gameName }),
      });
      
      const data = await response.json();

      if (response.ok) {
        let starterCode = '';
        if (data.starter_code) {
          starterCode = data.starter_code;
          if (starterCode.startsWith("\n")) {
            starterCode = starterCode.slice(1);
          }
        }

        return {
          success: true,
          starterCode,
          instructions: data.game_instructions,
          rewardSchema: data.reward_schema ?? null,
          rewardInstructions: data.reward_instructions ?? "",
        };
      } else {
        return {
          success: false,
          error: "Failed to get game instructions"
        };
      }
    } catch (error) {
      console.error("Error fetching game instructions:", error);
      return { 
        success: false, 
        error: "Network error while fetching instructions" 
      };
    }
  }, [apiUrl]);
  
  /**
   * Submit code for evaluation
   * @param {string} code - The agent code to submit
   * @param {Object} [options]
   * @param {boolean} [options.generateHint] - Ask the backend to also generate a hint
   */
  const submitCode = useCallback(async (code, { generateHint = false } = {}) => {
    if (!code || code.trim() === "") {
      toast.error("Please enter some code before submitting");
      return {
        success: false,
        error: "Empty code submission"
      };
    }

    setIsLoading(true);

    try {
      const url = `${apiUrl}/user/submit-agent${generateHint ? "?generate_hint=true" : ""}`;
      const response = await authFetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ code }),
      });

      const data = await response.json();

      if (response.ok) {
        return {
          success: true,
          output: data.results,
          feedback: data.feedback,
          hint: data.hint ?? null,
          hint_available: data.hint_available ?? false,
          // True when a hint was requested but the code passed validation,
          // so the backend skipped the hint without consuming the attempt.
          hint_cancelled: data.hint_cancelled ?? false
        };
      } else {
        // Failed validation is a 400 whose body carries the hint fields
        // next to the standard error detail.
        toast.error(data.detail || "Error in submission");
        return {
          success: false,
          error: data.detail,
          hint: data.hint ?? null,
          hint_available: data.hint_available ?? false,
          hint_cancelled: false
        };
      }
    } catch (error) {
      console.error("Error during submission:", error);
      toast.error("Network error during submission. Please try again.");
      return { 
        success: false, 
        error: "Network error during submission" 
      };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken]);
  
  return {
    isLoading,
    getLatestSubmission,
    getTeamSubmissions,
    getGameInstructions,
    submitCode
  };
};

export default useSubmissionAPI;
