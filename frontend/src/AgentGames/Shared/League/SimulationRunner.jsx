// src/AgentGames/Shared/League/SimulationRunner.jsx
import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { addSimulationResult } from '../../../slices/leaguesSlice';
import useLeagueAPI from '../hooks/useLeagueAPI';

/**
 * Component for running league simulations
 * 
 * @param {Object} props - Component props
 * @param {Object} props.league - The current league object
 * @param {string} props.userRole - User role ('admin' or 'institution')
 */
const SimulationRunner = ({ league, userRole }) => {
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
    <div className="bg-white rounded-lg shadow-lg p-4">
      <h2 className="text-xl font-semibold text-ui-dark mb-4">Run Simulation</h2>
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <button
            onClick={handleSimulation}
            disabled={isDisabled}
            className={`
              flex-grow px-6 py-3 rounded-lg font-semibold text-lg transition-colors
              focus:ring-2 focus:ring-offset-2 outline-none
              ${isDisabled
                ? "bg-ui-light text-ui cursor-not-allowed"
                : "bg-notice-orange hover:bg-notice-orange/90 text-white"}
            `}
          >
            {isLoading ? "RUNNING..." : "RUN SIMULATION"}
          </button>

          <input
            type="number"
            value={simulationNumber}
            onChange={handleNumberChange}
            min="1"
            max="10000"
            disabled={isLoading || isPlaceholder}
            className="w-24 p-2 border border-ui-light rounded-lg text-lg shadow-sm
                     focus:ring-2 focus:ring-primary focus:border-primary outline-none
                     disabled:bg-ui-light disabled:cursor-not-allowed"
          />
        </div>

        {league && (
          <div className="text-sm text-ui">
            {isPlaceholder ? (
              <>
                The "unassigned" league is a placeholder for teams without a
                league — simulations cannot be run on it.
              </>
            ) : (
              <>
                Selected League: {league.name} ({league.game})
              </>
            )}
          </div>
        )}

        {!isPlaceholder && (
          <div className="text-xs text-ui bg-ui-light/60 rounded-md px-3 py-2">
            Simulation runs are capped at 10 minutes. If the requested number of
            games would take longer, we run as many complete games as fit in the
            time limit and report the actual count — a run never stops
            mid-game, so the results stay fair.
          </div>
        )}
      </div>
    </div>
  );
};

export default SimulationRunner;