// src/AgentGames/Shared/hooks/useLeagueAPI.js
import { useState } from 'react';
import { useSelector } from 'react-redux';
import { toast } from 'react-toastify';

/**
 * Hook for handling league-related API calls
 * @param {string} userRole - The role of the current user ('admin' or 'institution')
 * @returns {Object} API methods and loading state
 */
export const useLeagueAPI = (userRole) => {
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const [isLoading, setIsLoading] = useState(false);
  
  /**
   * Run a simulation for the specified league
   */
  const runSimulation = async (params) => {
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
  };
  
  /**
   * Create a new league
   */
  const createLeague = async (leagueData) => {
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
  };
  
  /**
   * Publish league results
   */
  const publishResults = async (publishData) => {
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
  };
  
  /**
   * Update league expiry date
   */
  const updateExpiryDate = async (leagueName, expiryDate) => {
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
  };
  
  /**
   * Assign team to league
   */
  const assignTeamToLeague = async (teamId, leagueId) => {
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
  };
  
  return {
    isLoading,
    runSimulation,
    createLeague,
    publishResults,
    updateExpiryDate,
    assignTeamToLeague
  };
};

export default useLeagueAPI;