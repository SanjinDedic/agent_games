// src/AgentGames/Shared/hooks/useLeagueAPI.js
import { useState, useCallback } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { toast } from 'react-toastify';
import { setLeagues, setCurrentLeague } from '../../../slices/leaguesSlice';

/**
 * Hook for handling league-related API calls
 * @param {string} userRole - The role of the current user ('admin' or 'institution')
 * @returns {Object} API methods and loading state
 */
export const useLeagueAPI = (userRole) => {
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const [isLoading, setIsLoading] = useState(false);
  
  /**
   * Get info about a league using token
   */
  const getLeagueInfo = useCallback(async (leagueToken) => {
    try {
      const response = await fetch(`${apiUrl}/user/league-info/${leagueToken}`);
      const data = await response.json();
      
      if (data.status === 'success') {
        return { success: true, data: data.data };
      } else {
        return { success: false, error: data.message || 'Failed to fetch league info' };
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
      const response = await fetch(`${apiUrl}/user/get-all-leagues`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });
      
      const data = await response.json();
      
      if (data.status === "success" && data.data?.leagues) {
        dispatch(setLeagues(data.data.leagues));
        return { success: true, leagues: data.data.leagues };
      } else {
        toast.error(data.message || 'Failed to fetch leagues');
        return { success: false, error: data.message || 'Failed to fetch leagues' };
      }
    } catch (error) {
      console.error('Error fetching leagues:', error);
      toast.error("Network error while fetching leagues");
      return { success: false, error: "Network error" };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken, dispatch]);

  /**
   * Assign current user to a league
   */
  const assignToLeague = useCallback(async (leagueName) => {
    if (!leagueName) {
      toast.error("League not selected");
      return { success: false, error: "League not selected" };
    }
    
    setIsLoading(true);
    
    try {
      const response = await fetch(`${apiUrl}/user/league-assign`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ name: leagueName }),
      });
      
      const data = await response.json();
      
      if (data.status === "success") {
        toast.success(data.message || 'Successfully joined league');
        return { success: true };
      } else {
        toast.error(data.message || 'Failed to join league');
        return { success: false, error: data.message };
      }
    } catch (error) {
      console.error('Error assigning to league:', error);
      toast.error("Network error occurred");
      return { success: false, error: "Network error" };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken]);
  
  /**
   * Run a simulation for the specified league
   */
  const runSimulation = useCallback(async (params) => {
    setIsLoading(true);
    const toastId = toast.loading("Running simulation...");
    
    try {
      // Both admin and institution use the same endpoint
      const response = await fetch(`${apiUrl}/institution/run-simulation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify(params),
      });
      
      const data = await response.json();
      
      if (data.status === "success") {
        toast.update(toastId, {
          render: data.message,
          type: "success",
          isLoading: false,
          autoClose: 2000
        });
        return { success: true, data: data.data };
      } else {
        toast.update(toastId, {
          render: data.message || 'Failed to run simulation',
          type: "error",
          isLoading: false,
          autoClose: 2000
        });
        return { success: false, error: data.message };
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
  }, [apiUrl, accessToken]);
  
  /**
   * Create a new league
   */
  const createLeague = useCallback(async (leagueData) => {
    setIsLoading(true);
    
    try {
      // Both admin and institution use the same endpoint
      const response = await fetch(`${apiUrl}/institution/league-create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify(leagueData),
      });
      
      const data = await response.json();
      
      if (data.status === "success") {
        toast.success(data.message);
        return { success: true, data: data.data };
      } else {
        toast.error(data.message || 'Failed to create league');
        return { success: false, error: data.message };
      }
    } catch (error) {
      console.error('Error creating league:', error);
      toast.error('Failed to create league');
      return { success: false, error: "Network error" };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken]);
  
  /**
   * Publish league results
   */
  const publishResults = useCallback(async (publishData) => {
    setIsLoading(true);
    
    try {
      const response = await fetch(`${apiUrl}/institution/publish-results`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify(publishData),
      });
      
      const data = await response.json();
      
      if (data.status === "success") {
        toast.success(data.message);
        return { success: true };
      } else {
        toast.error(data.message || 'Failed to publish results');
        return { success: false, error: data.message };
      }
    } catch (error) {
      console.error('Error publishing results:', error);
      toast.error('Network error while publishing results');
      return { success: false, error: "Network error" };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken]);
  
  /**
   * Update league expiry date
   */
  const updateExpiryDate = useCallback(async (leagueName, expiryDate) => {
    setIsLoading(true);
    
    try {
      const response = await fetch(`${apiUrl}/institution/update-expiry-date`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({ 
          date: expiryDate,
          league: leagueName 
        }),
      });
      
      const data = await response.json();
      
      if (data.status === "success") {
        toast.success(data.message);
        return { success: true };
      } else {
        toast.error(data.message || 'Failed to update expiry date');
        return { success: false, error: data.message };
      }
    } catch (error) {
      console.error('Error updating expiry date:', error);
      toast.error('Failed to update expiry date');
      return { success: false, error: "Network error" };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken]);
  
  /**
   * Assign team to league
   */
  const assignTeamToLeague = useCallback(async (teamId, leagueId) => {
    setIsLoading(true);
    
    try {
      const response = await fetch(`${apiUrl}/institution/assign-team-to-league`, {
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
      
      if (data.status === "success") {
        toast.success(data.message);
        return { success: true };
      } else {
        toast.error(data.message || 'Failed to assign team to league');
        return { success: false, error: data.message };
      }
    } catch (error) {
      console.error('Error assigning team to league:', error);
      toast.error('Failed to assign team to league');
      return { success: false, error: "Network error" };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, accessToken]);
  
  return {
    isLoading,
    getLeagueInfo,
    fetchUserLeagues,
    assignToLeague,
    runSimulation,
    createLeague,
    publishResults,
    updateExpiryDate,
    assignTeamToLeague
  };
};

export default useLeagueAPI;