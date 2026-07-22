// src/AgentGames/Shared/hooks/useTeamAPI.js
import { useCallback } from 'react';
import { useSelector } from 'react-redux';
import { authFetch } from '../../../utils/authFetch';
import { selectToken } from '../../../slices/authSlice';

/**
 * Hook for team-scoped aggregate reads. getTeamData backs the student
 * landing page: identity, league, per-tutorial progress, and agent-game
 * stats in one call.
 */
export const useTeamAPI = () => {
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);

  const getTeamData = useCallback(async () => {
    try {
      const response = await authFetch(`${apiUrl}/user/team-data`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        },
      });

      const data = await response.json();

      if (response.ok) {
        return { success: true, data };
      }
      return {
        success: false,
        error: data.detail || "Failed to load your home page",
      };
    } catch (error) {
      console.error("Error loading team data:", error);
      return { success: false, error: "Network error while loading your home page" };
    }
  }, [apiUrl, accessToken]);

  return { getTeamData };
};

export default useTeamAPI;
