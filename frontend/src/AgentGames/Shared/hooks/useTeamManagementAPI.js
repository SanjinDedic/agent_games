// src/AgentGames/Shared/hooks/useTeamManagementAPI.js
import { useCallback } from 'react';
import { useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import { selectToken } from '../../../slices/authSlice';
import { authFetch } from '../../../utils/authFetch';
import { useTerms } from '../terminology';

/**
 * Institution team management: the roster reads plus the create / delete /
 * password-reset writes. Every call returns { success, data | error }.
 * The hook toasts failures (the copy is identical at every call site) and
 * stays silent on success so callers keep their contextual wording.
 * Student-side reads live in useTeamAPI — don't merge the two.
 */
export const useTeamManagementAPI = () => {
  const T = useTerms();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);

  const request = useCallback(
    async (path, options, errorFallback) => {
      try {
        const response = await authFetch(`${apiUrl}${path}`, {
          ...options,
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${accessToken}`,
          },
        });
        const data = await response.json();
        if (response.ok) {
          return { success: true, data };
        }
        toast.error(data.detail || errorFallback);
        return { success: false, error: data.detail || errorFallback };
      } catch (error) {
        console.error(`Error calling ${path}:`, error);
        toast.error(errorFallback);
        return { success: false, error: errorFallback };
      }
    },
    [apiUrl, accessToken]
  );

  const getAllTeams = useCallback(
    () => request('/institution/get-all-teams', {}, `Failed to load ${T.teams}`),
    [request, T]
  );

  const getUnassignedTeams = useCallback(async () => {
    const result = await getAllTeams();
    if (!result.success) return result;
    const teams = (result.data.teams || []).filter(
      (t) => !t.league || t.league === 'unassigned'
    );
    return { success: true, data: { teams } };
  }, [getAllTeams]);

  const createTeam = useCallback(
    async ({ name, password, school_name }) => {
      if (!name?.trim() || !password?.trim()) {
        const error = `${T.Team} name and password are required`;
        toast.error(error);
        return { success: false, error };
      }
      return request(
        '/institution/team-create',
        {
          method: 'POST',
          body: JSON.stringify({
            name,
            password,
            school_name: school_name || 'Not Available',
          }),
        },
        `Failed to add ${T.team}`
      );
    },
    [request, T]
  );

  const deleteTeam = useCallback(
    (teamId) =>
      request(
        '/institution/delete-team',
        { method: 'POST', body: JSON.stringify({ id: teamId }) },
        `Failed to delete ${T.team}`
      ),
    [request, T]
  );

  const resetTeamPassword = useCallback(
    (teamId) =>
      request(
        '/institution/team-password-reset',
        { method: 'POST', body: JSON.stringify({ team_id: teamId }) },
        'Failed to generate reset link'
      ),
    [request]
  );

  return { getAllTeams, getUnassignedTeams, createTeam, deleteTeam, resetTeamPassword };
};

export default useTeamManagementAPI;
