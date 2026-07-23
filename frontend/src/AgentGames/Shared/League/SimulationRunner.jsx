// src/AgentGames/Shared/League/SimulationRunner.jsx
import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { addSimulationResult } from '../../../slices/leaguesSlice';
import useLeagueAPI from '../hooks/useLeagueAPI';
import { useTerms } from '../terminology';

/**
 * Component for running league simulations
 * 
 * @param {Object} props - Component props
 * @param {Object} props.league - The current league object
 * @param {string} props.userRole - User role ('admin' or 'institution')
 */
const SimulationRunner = ({ league, userRole }) => {
  const T = useTerms();
  const dispatch = useDispatch();
  const rewards = useSelector((state) => state.leagues.currentRewards);
  const [simulationNumber, setSimulationNumber] = useState(1);

  // Use the shared API hook
  const { isLoading, runSimulation } = useLeagueAPI(userRole);

  // The auto-created "unassigned" league is a placeholder and cannot be simulated
  const isPlaceholder = league?.name?.toLowerCase() === "unassigned";
  const isDisabled = isLoading || !league?.id || isPlaceholder;

  // Input validation
  const handleNumberChange = (event) => {
    const value = parseInt(event.target.value, 10);
    if (value > 0 && value <= 10000) {
      setSimulationNumber(value);
    }
  };

  const handleSimulation = async () => {
    if (!league?.id || isPlaceholder) {
      return;
    }

    const result = await runSimulation({
      num_simulations: simulationNumber,
      league_id: league.id,
      custom_rewards: rewards,
    });

    if (result.success) {
      dispatch(addSimulationResult(result.data));
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex flex-col lg:flex-row lg:items-end gap-4">
        <div>
          <label
            htmlFor="simulation-game-count"
            className="block text-sm font-medium text-ui mb-1"
          >
            Games per run
          </label>
          <input
            id="simulation-game-count"
            type="number"
            value={simulationNumber}
            onChange={handleNumberChange}
            min="1"
            max="10000"
            disabled={isLoading || isPlaceholder}
            className="w-32 p-3 border border-ui-light rounded-lg text-lg shadow-sm
                     focus:ring-2 focus:ring-primary focus:border-primary outline-none
                     disabled:bg-ui-light disabled:cursor-not-allowed"
          />
        </div>

        <button
          onClick={handleSimulation}
          disabled={isDisabled}
          className={`
            px-8 py-3 rounded-lg font-semibold text-lg transition-colors
            focus:ring-2 focus:ring-offset-2 outline-none
            ${isDisabled
              ? "bg-ui-light text-ui cursor-not-allowed"
              : "bg-notice-orange hover:bg-notice-orange/90 text-white"}
          `}
        >
          {isLoading ? "RUNNING..." : "RUN SIMULATION"}
        </button>

        {league && (
          <div className="flex-1 text-sm text-ui lg:pb-3">
            {isPlaceholder ? (
              <>
                {`The "unassigned" ${T.league} is a placeholder for ${T.teams} without a ${T.league} — simulations cannot be run on it.`}
              </>
            ) : (
              <>
                <span className="font-medium text-ui-dark">{league.name}</span>
                {` · ${league.game} · every ${T.team}'s latest agent competes`}
              </>
            )}
          </div>
        )}
      </div>

      {!isPlaceholder && (
        <details className="mt-3 text-sm text-ui">
          <summary className="cursor-pointer hover:text-ui-dark">
            Why a run can return fewer games than requested
          </summary>
          <p className="mt-2 text-xs bg-ui-light/60 rounded-md px-3 py-2">
            Simulation runs are capped at 10 minutes. If the requested number of
            games would take longer, we run as many complete games as fit in the
            time limit and report the actual count — a run never stops
            mid-game, so the results stay fair.
          </p>
        </details>
      )}
    </div>
  );
};

export default SimulationRunner;