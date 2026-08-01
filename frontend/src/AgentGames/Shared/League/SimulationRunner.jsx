// src/AgentGames/Shared/League/SimulationRunner.jsx
import React, { useState } from 'react';
import { useSelector } from 'react-redux';
import CustomRewards from '../Common/CustomRewards';
import useSimulationRun from '../hooks/useSimulationRun';
import { isSimulationSupported } from '../../../pyodide/games/index';
import { useTerms } from '../terminology';

/**
 * Component for running league simulations in the browser (Pyodide).
 *
 * @param {Object} props - Component props
 * @param {Object} props.league - The current league object
 * @param {string} props.userRole - User role ('admin' or 'institution')
 */
const SimulationRunner = ({ league, userRole }) => {
  const T = useTerms();
  const rewards = useSelector((state) => state.leagues.currentRewards);
  const [simulationNumber, setSimulationNumber] = useState(1);

  const { isRunning, progress, runSimulation, cancelRun } =
    useSimulationRun(userRole);

  // The auto-created "unassigned" league is a placeholder and cannot be simulated
  const isPlaceholder = league?.name?.toLowerCase() === "unassigned";
  // Games are ported to the in-browser runner one at a time; the rest are
  // disabled until their engine ships in frontend/src/pyodide/games/.
  const isUnsupportedGame = Boolean(league?.game) && !isSimulationSupported(league.game);
  const isDisabled = isRunning || !league?.id || isPlaceholder || isUnsupportedGame;

  // Input validation
  const handleNumberChange = (event) => {
    const value = parseInt(event.target.value, 10);
    if (value > 0 && value <= 10000) {
      setSimulationNumber(value);
    }
  };

  const handleSimulation = async () => {
    if (!league?.id || isPlaceholder || isUnsupportedGame) {
      return;
    }

    await runSimulation({
      league,
      numSimulations: simulationNumber,
      customRewards: rewards,
    });
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
            disabled={isRunning || isPlaceholder || isUnsupportedGame}
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
          {isRunning ? "RUNNING..." : "RUN SIMULATION"}
        </button>

        {isRunning && (
          <button
            onClick={cancelRun}
            className="px-4 py-3 rounded-lg font-semibold text-lg transition-colors
                     border border-ui-light text-ui hover:text-ui-dark hover:border-ui
                     focus:ring-2 focus:ring-offset-2 outline-none"
          >
            CANCEL
          </button>
        )}

        {league && (
          <div className="flex-1 text-sm text-ui lg:pb-3">
            {isPlaceholder ? (
              <>
                {`The "unassigned" ${T.league} is a placeholder for ${T.teams} without a ${T.league} — simulations cannot be run on it.`}
              </>
            ) : isUnsupportedGame ? (
              <>
                {`Simulations for ${league.game} haven't been migrated to the in-browser runner yet.`}
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

      {isRunning && progress && (
        <div className="mt-4">
          <div className="flex justify-between text-xs text-ui mb-1">
            <span>
              {`${progress.completed.toLocaleString()} / ${progress.requested.toLocaleString()} games`}
            </span>
          </div>
          <div className="w-full bg-ui-light rounded-full h-2">
            <div
              className="bg-notice-orange h-2 rounded-full transition-all"
              style={{
                width: `${Math.round((100 * progress.completed) / progress.requested)}%`,
              }}
            />
          </div>
        </div>
      )}

      {/* Rewards are a run parameter, so they live with the run controls */}
      {!isPlaceholder && !isUnsupportedGame && <CustomRewards />}

      {!isPlaceholder && !isUnsupportedGame && (
        <details className="mt-3 text-sm text-ui">
          <summary className="cursor-pointer hover:text-ui-dark">
            Why a run can return fewer games than requested
          </summary>
          <p className="mt-2 text-xs bg-ui-light/60 rounded-md px-3 py-2">
            Games run in your browser. Cancelling a run keeps the complete
            games already played and reports the actual count — a run never
            stops mid-game, so the results stay fair.
          </p>
        </details>
      )}
    </div>
  );
};

export default SimulationRunner;
