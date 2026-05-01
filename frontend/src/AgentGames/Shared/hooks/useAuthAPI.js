// src/AgentGames/Shared/hooks/useAuthAPI.js
import { useState, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { jwtDecode } from 'jwt-decode';
import { login as loginAction } from '../../../slices/authSlice';
import { setCurrentTeam } from '../../../slices/teamsSlice';
import { toast } from 'react-toastify';

export const useAuthAPI = () => {
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const [isLoading, setIsLoading] = useState(false);
  const dispatch = useDispatch();

  // Team login - for regular login flow
  const teamLogin = useCallback(async (username, password) => {
    setIsLoading(true);

    try {
      const response = await fetch(`${apiUrl}/auth/team-login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: username, password: password }),
      });

      const data = await response.json();

      if (data.status === "success") {
        const decoded = jwtDecode(data.data.access_token);

        // Handle login state
        dispatch(loginAction({
          token: data.data.access_token,
          name: decoded.sub,
          role: decoded.role,
          exp: decoded.exp,
          is_demo: false,
        }));

        // Set current team
        dispatch(setCurrentTeam(username));

        return { success: true };
      } else {
        return { success: false, error: data.message };
      }
    } catch (error) {
      console.error('Error during login:', error);
      return { success: false, error: "Network error during login" };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, dispatch]);

  // Shared dispatcher for both signup endpoints. Both responses carry the
  // canonical team name in data.team_name (server-assigned for school
  // leagues, echoed for the classic flow), so the auth state setup is
  // identical.
  const dispatchSignup = useCallback(async (endpoint, body) => {
    setIsLoading(true);

    try {
      const response = await fetch(`${apiUrl}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (data.status === 'success') {
        const decoded = jwtDecode(data.data.access_token);
        const teamName = data.data.team_name;

        dispatch(loginAction({
          token: data.data.access_token,
          name: teamName,
          role: 'student',
          exp: decoded.exp,
          is_demo: false,
        }));
        dispatch(setCurrentTeam(teamName));

        toast.success(data.message || 'Signed up successfully!');

        return {
          success: true,
          leagueId: data.data.league_id,
          teamName,
        };
      }
      return { success: false, error: data.message || 'Failed to sign up' };
    } catch (error) {
      console.error('Error during signup:', error);
      return { success: false, error: 'Network error during signup' };
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, dispatch]);

  // Classic (free-text) signup flow
  const directSignup = useCallback(
    (teamName, password, leagueToken, schoolName) =>
      dispatchSignup('/user/direct-league-signup', {
        team_name: teamName,
        password,
        signup_token: leagueToken,
        school_name: schoolName,
      }),
    [dispatchSignup],
  );

  // School-league signup flow — server assigns the team name
  const directSchoolSignup = useCallback(
    (leagueToken, schoolName, password) =>
      dispatchSignup('/user/direct-school-league-signup', {
        signup_token: leagueToken,
        school_name: schoolName,
        password,
      }),
    [dispatchSignup],
  );

  return {
    isLoading,
    teamLogin,
    directSignup,
    directSchoolSignup,
  };
};

export default useAuthAPI;
