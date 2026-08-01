// src/AgentGames/Shared/hooks/useSimulationRun.js
import { useCallback, useRef, useState } from 'react';
import { useDispatch } from 'react-redux';
import { toast } from 'react-toastify';
import { addSimulationResult } from '../../../slices/leaguesSlice';
import { startLeagueSimulation } from '../../../pyodide/simulationRunnerClient';
import useLeagueAPI from './useLeagueAPI';

/**
 * Orchestrates one in-browser league simulation run:
 * fetch every team's latest code → run the games in the Pyodide worker
 * (chunked, with progress + cancel) → persist the aggregate through
 * /institution/save-simulation-results → dispatch the saved run (with the
 * locally-computed player_feedback merged in, since the server never stores
 * it) into the same addSimulationResult flow the old Celery path used.
 *
 * @param {string} userRole - 'admin' or 'institution' (passed to useLeagueAPI)
 */
export const useSimulationRun = (userRole) => {
  const dispatch = useDispatch();
  const { fetchLeagueSubmissions, saveSimulationResults } =
    useLeagueAPI(userRole);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(null); // {completed, requested} | null
  const cancelRef = useRef(null);

  const cancelRun = useCallback(() => {
    cancelRef.current?.();
  }, []);

  const runSimulation = useCallback(
    async ({ league, numSimulations, customRewards }) => {
      setIsRunning(true);
      setProgress(null);
      const toastId = toast.loading('Running simulation...');
      const fail = (message) => {
        toast.update(toastId, {
          render: message,
          type: 'error',
          isLoading: false,
          autoClose: 4000,
        });
        return { success: false, error: message };
      };

      try {
        const fetched = await fetchLeagueSubmissions(league.id);
        if (!fetched.success) return fail(fetched.error);

        const run = startLeagueSimulation({
          gameName: league.game,
          submissions: fetched.submissions,
          numSimulations,
          customRewards,
          onProgress: setProgress,
        });
        cancelRef.current = run.cancel;
        const outcome = await run.promise;

        if (outcome.kind === 'error') {
          // The Pyodide runtime itself failed — there is no server-side
          // fallback anymore, so all we can do is say so.
          console.error('Simulation runtime failure:', outcome.reason);
          return fail(
            'In-browser simulation unavailable — reload the page and try again.'
          );
        }

        const { envelope } = outcome;
        if (envelope.status === 'error') {
          // Same failure UX as the old worker path's 400: surface the
          // harness message, store nothing.
          return fail(envelope.message || 'Simulation failed');
        }

        const results = envelope.simulation_results;
        const saved = await saveSimulationResults({
          league_id: league.id,
          num_simulations: results.num_simulations,
          requested_simulations: results.requested_simulations,
          capped: results.capped,
          custom_rewards: customRewards,
          total_points: results.total_points,
          table: results.table,
          strategies: results.strategies,
          feedback: envelope.feedback,
        });
        if (!saved.success) return fail(saved.error);

        dispatch(
          addSimulationResult({
            ...saved.data,
            player_feedback: envelope.player_feedback,
          })
        );

        if (envelope.skipped?.length) {
          const names = envelope.skipped.map((s) => s.team).join(', ');
          toast.info(`Agents that failed to load were skipped: ${names}`);
        }
        toast.update(toastId, {
          render: 'Simulation completed successfully',
          type: 'success',
          isLoading: false,
          autoClose: 2000,
        });
        return { success: true, data: saved.data };
      } catch (error) {
        console.error('Simulation error:', error);
        return fail('Error running simulation');
      } finally {
        cancelRef.current = null;
        setIsRunning(false);
        setProgress(null);
      }
    },
    [dispatch, fetchLeagueSubmissions, saveSimulationResults]
  );

  return { isRunning, progress, runSimulation, cancelRun };
};

export default useSimulationRun;
