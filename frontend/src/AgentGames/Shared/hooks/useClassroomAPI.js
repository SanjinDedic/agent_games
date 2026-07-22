// src/AgentGames/Shared/hooks/useClassroomAPI.js
import { useCallback } from 'react';
import { useSelector } from 'react-redux';
import { selectToken } from '../../../slices/authSlice';
import { authFetch } from '../../../utils/authFetch';

/**
 * Hook for the classroom workspace endpoints. Every call returns
 * { success, data | error } and leaves toasts to the caller.
 */
export const useClassroomAPI = () => {
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);

  const get = useCallback(
    async (path) => {
      try {
        const response = await authFetch(`${apiUrl}${path}`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        const data = await response.json();
        if (response.ok) {
          return { success: true, data };
        }
        return { success: false, error: data.detail || 'Request failed' };
      } catch (error) {
        console.error(`Error fetching ${path}:`, error);
        return { success: false, error: 'Network error' };
      }
    },
    [apiUrl, accessToken]
  );

  const getClassroomProgress = useCallback(
    (leagueId) => get(`/institution/classroom/${leagueId}/progress`),
    [get]
  );

  const getTutorialMatrix = useCallback(
    (leagueId) => get(`/institution/classroom/${leagueId}/tutorial-matrix`),
    [get]
  );

  const getStudentSummary = useCallback(
    (teamId) => get(`/institution/student/${teamId}/summary`),
    [get]
  );

  const getStudentAgentSubmissions = useCallback(
    (teamId) => get(`/institution/student/${teamId}/agent-submissions`),
    [get]
  );

  const getStudentExerciseSubmissions = useCallback(
    (teamId, exerciseId) =>
      get(
        `/institution/student/${teamId}/exercise-submissions?exercise_id=${exerciseId}`
      ),
    [get]
  );

  return {
    getClassroomProgress,
    getTutorialMatrix,
    getStudentSummary,
    getStudentAgentSubmissions,
    getStudentExerciseSubmissions,
  };
};

export default useClassroomAPI;
