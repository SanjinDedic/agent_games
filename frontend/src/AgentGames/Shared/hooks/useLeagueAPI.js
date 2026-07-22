// src/AgentGames/Shared/hooks/useLeagueAPI.js
import { useState, useCallback } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { toast } from 'react-toastify';
import { setLeagues, setResults, clearResults, updateLeagueInfo as updateLeagueInfoAction, setRewardMeta } from '../../../slices/leaguesSlice';
import { selectToken, setToken } from '../../../slices/authSlice';
import { authFetch } from '../../../utils/authFetch';
import { useTerms } from '../terminology';

/**
 * Hook for handling league-related API calls
 * @param {string} userRole - The role of the current user ('admin' or 'institution')
 * @returns {Object} API methods and loading state
 */
export const useLeagueAPI = (userRole) => {
  const dispatch = useDispatch();
  const T = useTerms();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);
  const [isLoading, setIsLoading] = useState(false);
  
  /**
   * Get info about a league using token
   */
  const getLeagueInfo = useCallback(async (leagueToken) => {
    try {
      const response = await fetch(`${apiUrl}/user/league-info/${leagueToken}`);
      const data = await response.json();

      if (response.ok) {
        return { success: true, data };
      } else {
        return { success: false, error: data.detail || 'Failed to fetch league info' };
      }
    } catch (error) {
      console.error('Error fetching league info:', error);
      return { success: false, error: "Network error" };
    }
  }, [apiUrl]);

  /**
   * Fetch all leagues for current user
   */
  const fetchUserLeagues = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await authFetch(`${apiUrl}/user/get-all-leagues`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });
      
      const data = await response.json();

      if (response.ok && data.leagues) {
        dispatch(setLeagues(data.leagues));
        return { success: true, leagues: data.leagues };
      } else {
        toast.error(data.detail || `Failed to fetch ${T.leagues}`);
        return { success: false, error: data.detail || `Failed to fetch ${T.leagues}` };
      }
    } catch (error) {
      console.error('Error fetching leagues:', error);
      toast.error(`Network error while fetching ${T.leagues}`);
      return { success: false, error: "Network error" };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken, dispatch, T]);

  /**
   * Assign current user to a league
   */
  const assignToLeague = useCallback(async (leagueId) => {
    if (!leagueId) {
      toast.error(`${T.League} not selected`);
      return { success: false, error: `${T.League} not selected` };
    }

    setIsLoading(true);

    try {
      const response = await authFetch(`${apiUrl}/user/league-assign`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ league_id: leagueId }),
      });
      
      const data = await response.json();

      if (response.ok) {
        if (data.access_token) {
          dispatch(setToken(data.access_token));
        }
        toast.success(data.message || `Successfully joined ${T.league}`);
        return { success: true };
      } else {
        toast.error(data.detail || `Failed to join ${T.league}`);
        return { success: false, error: data.detail };
      }
    } catch (error) {
      console.error('Error assigning to league:', error);
      toast.error("Network error occurred");
      return { success: false, error: "Network error" };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken, dispatch, T]);

  /**
   * Fetch all simulation results for a league
   */
  const fetchLeagueResults = useCallback(async (leagueId) => {
    if (!leagueId) return { success: false, error: 'league_id required' };
    try {
      const response = await authFetch(
        `${apiUrl}/institution/get-all-league-results`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({ league_id: leagueId }),
        },
      );
      const data = await response.json();
      if (response.ok) {
        const results = data.results || [];
        if (results.length === 0) {
          dispatch(clearResults());
          toast.info(`No results in the selected ${T.League}`);
        } else {
          dispatch(setResults(results));
        }
        return { success: true, results };
      }
      toast.error(data.detail || `Failed to fetch ${T.league} results`);
      dispatch(clearResults());
      return { success: false, error: data.detail };
    } catch (error) {
      console.error('Error fetching league results:', error);
      return { success: false, error: 'Network error' };
    }
  }, [apiUrl, accessToken, dispatch, T]);

  /**
   * Run a simulation for the specified league
   */
  const runSimulation = useCallback(async (params) => {
    setIsLoading(true);
    const toastId = toast.loading("Running simulation...");
    
    try {
      // Both admin and institution use the same endpoint
      const response = await authFetch(`${apiUrl}/institution/run-simulation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify(params),
      });
      
      const data = await response.json();

      if (response.ok) {
        toast.update(toastId, {
          render: "Simulation completed successfully",
          type: "success",
          isLoading: false,
          autoClose: 2000
        });
        return { success: true, data };
      } else {
        toast.update(toastId, {
          render: data.detail || 'Failed to run simulation',
          type: "error",
          isLoading: false,
          autoClose: 2000
        });
        return { success: false, error: data.detail };
      }
    } catch (error) {
      console.error('Simulation error:', error);
      toast.update(toastId, {
        render: "Error running simulation",
        type: "error",
        isLoading: false,
        autoClose: 2000
      });
      return { success: false, error: "Network error" };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken, T]);
  
  /**
   * Create a new league
   */
  const createLeague = useCallback(async (leagueData) => {
    setIsLoading(true);
    
    try {
      // Both admin and institution use the same endpoint
      const response = await authFetch(`${apiUrl}/institution/league-create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify(leagueData),
      });
      
      const data = await response.json();

      if (response.ok) {
        toast.success(`${T.League} created successfully`);
        return { success: true, data };
      } else {
        toast.error(data.detail || `Failed to create ${T.league}`);
        return { success: false, error: data.detail };
      }
    } catch (error) {
      console.error('Error creating league:', error);
      toast.error(`Failed to create ${T.league}`);
      return { success: false, error: "Network error" };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken, T]);
  
  /**
   * Publish league results
   */
  const publishResults = useCallback(async (publishData) => {
    setIsLoading(true);
    
    try {
      //set publishData.feedback to none
      publishData.feedback = undefined

      const response = await authFetch(`${apiUrl}/institution/publish-results`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify(publishData),
      });
      
      const data = await response.json();

      if (response.ok) {
        toast.success(data.message);
        return {
          success: true,
          data  // Complete payload including message + publish_link
        };
      } else {
        toast.error(data.detail || 'Failed to publish results');
        return { success: false, error: data.detail };
      }
    } catch (error) {
      console.error('Error publishing results:', error);
      toast.error('Network error while publishing results');
      return { success: false, error: "Network error" };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken, T]);
  
  /**
   * Update league expiry date
   */
  const updateExpiryDate = useCallback(async (leagueId, expiryDate) => {
    setIsLoading(true);

    try {
      const response = await authFetch(`${apiUrl}/institution/update-expiry-date`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({
          date: expiryDate,
          league_id: leagueId,
        }),
      });
      
      const data = await response.json();

      if (response.ok) {
        toast.success(data.message);
        return { success: true };
      } else {
        toast.error(data.detail || 'Failed to update expiry date');
        return { success: false, error: data.detail };
      }
    } catch (error) {
      console.error('Error updating expiry date:', error);
      toast.error('Failed to update expiry date');
      return { success: false, error: "Network error" };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken, T]);
  
  /**
   * Update per-league markdown info block
   */
  const updateLeagueInfo = useCallback(async (leagueId, infoMarkdown) => {
    setIsLoading(true);
    try {
      const response = await authFetch(`${apiUrl}/institution/update-league-info`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          league_id: leagueId,
          info_markdown: infoMarkdown ?? '',
        }),
      });

      const data = await response.json();

      if (response.ok) {
        dispatch(updateLeagueInfoAction({
          league_id: leagueId,
          info_markdown: infoMarkdown ?? '',
        }));
        toast.success(data.message);
        return { success: true };
      }
      toast.error(data.detail || `Failed to update ${T.league} info`);
      return { success: false, error: data.detail };
    } catch (error) {
      console.error('Error updating league info:', error);
      toast.error(`Network error while updating ${T.league} info`);
      return { success: false, error: 'Network error' };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken, dispatch, T]);

  /**
   * Get the ids of the tutorials attached to a league
   */
  const getLeagueTutorials = useCallback(async (leagueId) => {
    try {
      const response = await authFetch(`${apiUrl}/institution/get-league-tutorials`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ league_id: leagueId }),
      });

      const data = await response.json();

      if (response.ok && Array.isArray(data.tutorial_ids)) {
        return { success: true, tutorialIds: data.tutorial_ids };
      }
      return { success: false, error: data.detail || `Failed to load ${T.league} ${T.tutorials}` };
    } catch (error) {
      console.error('Error loading league tutorials:', error);
      return { success: false, error: 'Network error' };
    }
  }, [apiUrl, accessToken, T]);

  /**
   * Replace the set of tutorials attached to a league
   */
  const updateLeagueTutorials = useCallback(async (leagueId, tutorialIds) => {
    setIsLoading(true);
    try {
      const response = await authFetch(`${apiUrl}/institution/update-league-tutorials`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ league_id: leagueId, tutorial_ids: tutorialIds }),
      });

      const data = await response.json();

      if (response.ok) {
        toast.success(data.message);
        return { success: true, tutorialIds: data.tutorial_ids };
      }
      toast.error(data.detail || `Failed to update ${T.league} ${T.tutorials}`);
      return { success: false, error: data.detail };
    } catch (error) {
      console.error('Error updating league tutorials:', error);
      toast.error(`Network error while updating ${T.league} ${T.tutorials}`);
      return { success: false, error: 'Network error' };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken, T]);

  /**
   * Assign team to league
   */
  const assignTeamToLeague = useCallback(async (teamId, leagueId) => {
    setIsLoading(true);
    
    try {
      const response = await authFetch(`${apiUrl}/institution/assign-team-to-league`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({
          team_id: parseInt(teamId),
          league_id: leagueId
        }),
      });
      
      const data = await response.json();

      if (response.ok) {
        toast.success(data.message);
        return { success: true };
      } else {
        toast.error(data.detail || `Failed to assign ${T.team} to ${T.league}`);
        return { success: false, error: data.detail };
      }
    } catch (error) {
      console.error('Error assigning team to league:', error);
      toast.error(`Failed to assign ${T.team} to ${T.league}`);
      return { success: false, error: "Network error" };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken, T]);

  /**
   * Unassign team (move to institution's 'unassigned' league)
   */
  const unassignTeam = useCallback(async (teamId) => {
    setIsLoading(true);
    try {
      const response = await authFetch(`${apiUrl}/institution/unassign-team`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({ team_id: parseInt(teamId) }),
      });

      const data = await response.json();

      if (response.ok) {
        toast.success(data.message);
        return { success: true };
      } else {
        toast.error(data.detail || `Failed to unassign ${T.team}`);
        return { success: false, error: data.detail };
      }
    } catch (error) {
      console.error('Error unassigning team:', error);
      toast.error(`Failed to unassign ${T.team}`);
      return { success: false, error: 'Network error' };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken, T]);

  /**
   * Delete a league
   */
  const deleteLeague = useCallback(async (leagueId) => {
    setIsLoading(true);

    try {
      const response = await authFetch(`${apiUrl}/institution/delete-league`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({ league_id: leagueId }),
      });
      
      const data = await response.json();

      if (response.ok) {
        // Refresh leagues after deletion
        await fetchUserLeagues();
        return { success: true, message: data.message };
      } else {
        toast.error(data.detail || `Failed to delete ${T.league}`);
        return { success: false, error: data.detail };
      }
    } catch (error) {
      console.error('Error deleting league:', error);
      toast.error(`Network error while deleting ${T.league}`);
      return { success: false, error: "Network error" };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken, fetchUserLeagues, T]);

  /**
   * Fetch reward schema + markdown for a game, dispatch into Redux.
   * Resets currentRewards so stale values from a previously selected game
   * aren't carried into a new simulation.
   */
  const fetchRewardMeta = useCallback(async (gameName) => {
    if (!gameName) {
      dispatch(setRewardMeta({ schema: null, instructions: "" }));
      return { success: false, error: "No game name" };
    }
    try {
      const response = await fetch(`${apiUrl}/user/get-game-instructions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ game_name: gameName }),
      });
      const data = await response.json();
      if (response.ok) {
        dispatch(setRewardMeta({
          schema: data.reward_schema ?? null,
          instructions: data.reward_instructions ?? "",
        }));
        return { success: true };
      }
      dispatch(setRewardMeta({ schema: null, instructions: "" }));
      return { success: false, error: data.detail || "Failed to fetch reward meta" };
    } catch (error) {
      console.error("Error fetching reward metadata:", error);
      dispatch(setRewardMeta({ schema: null, instructions: "" }));
      return { success: false, error: "Network error" };
    }
  }, [apiUrl, dispatch]);

  return {
    isLoading,
    getLeagueInfo,
    fetchUserLeagues,
    fetchLeagueResults,
    assignToLeague,
    runSimulation,
    createLeague,
    publishResults,
    updateExpiryDate,
    updateLeagueInfo,
    getLeagueTutorials,
    updateLeagueTutorials,
    assignTeamToLeague,
    unassignTeam,
    deleteLeague,
    fetchRewardMeta,
  };
};

export default useLeagueAPI;