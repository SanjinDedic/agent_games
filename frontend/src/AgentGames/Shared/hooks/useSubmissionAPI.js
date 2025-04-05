// src/AgentGames/Shared/hooks/useSubmissionAPI.js
import { useState, useCallback } from 'react';
import { useSelector } from 'react-redux';
import { toast } from 'react-toastify';

/**
 * Hook for handling code submission-related API calls
 * @returns {Object} API methods and loading state
 */
export const useSubmissionAPI = () => {
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const [isLoading, setIsLoading] = useState(false);
  
  /**
   * Get latest code submission
   */
  const getLatestSubmission = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/user/get-team-submission`, {
        headers: { 
          'Authorization': `Bearer ${accessToken}` 
        },
      });
      
      const data = await response.json();
      
      if (data.status === "success" && data.data && data.data.code) {
        return { 
          success: true, 
          hasSubmission: true, 
          code: data.data.code 
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
      
      if (data.status === "success" && data.data) {
        let starterCode = '';
        if (data.data.starter_code) {
          starterCode = data.data.starter_code;
          if (starterCode.startsWith("\n")) {
            starterCode = starterCode.slice(1);
          }
        }
        
        return { 
          success: true, 
          starterCode, 
          instructions: data.data.game_instructions 
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
   */
  const submitCode = useCallback(async (code) => {
    if (!code || code.trim() === "") {
      toast.error("Please enter some code before submitting");
      return { 
        success: false, 
        error: "Empty code submission" 
      };
    }
    
    setIsLoading(true);
    
    try {
      const response = await fetch(`${apiUrl}/user/submit-agent`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ code }),
      });
      
      const data = await response.json();
      
      if (data.status === "success") {
        return { 
          success: true, 
          output: data.data.results, 
          feedback: data.data.feedback 
        };
      } else {
        toast.error(data.message || "Error in submission");
        return { 
          success: false, 
          error: data.message 
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
    getGameInstructions,
    submitCode
  };
};

export default useSubmissionAPI;