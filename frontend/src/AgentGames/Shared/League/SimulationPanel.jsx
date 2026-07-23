// src/AgentGames/Shared/League/SimulationPanel.jsx
import React, { useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';

import { setCurrentSimulation } from "../../../slices/leaguesSlice";

import SimulationRunner from "./SimulationRunner";
import SimulationRunSummary from "./SimulationRunSummary";
import CustomRewards from "../Common/CustomRewards";
import ResultsDisplay from "../Utilities/ResultsDisplay";
import FeedbackSelector from "../../Feedback/FeedbackSelector";

import useClassroomAPI from "../hooks/useClassroomAPI";
import useLeagueAPI from "../hooks/useLeagueAPI";
import { useTerms } from "../terminology";

/**
 * Simulation controls + results for the league currently selected in Redux.
 * League selection lives with the caller: the admin/institution page keeps
 * its LeagueCardList column; the classroom workspace's Simulation tab renders
 * this panel alone.
 */
const SimulationPanel = ({ userRole }) => {
  const T = useTerms();
  const dispatch = useDispatch();
  const currentLeague = useSelector((state) => state.leagues.currentLeague);
  const allSimulations = useSelector(
    (state) => state.leagues.currentLeagueResults
  );
  const currentSimulation = useSelector(
    (state) => state.leagues.currentLeagueResultSelected
  );

  const api = useLeagueAPI(userRole);
  const { getClassroomProgress } = useClassroomAPI();

  // Roster names, used to show who had no agent in the selected run. Null when
  // unavailable (e.g. the progress call failed) — the block then stays hidden.
  const [roster, setRoster] = useState(null);

  // The "unassigned" league is a placeholder — no simulations, results or game
  const isPlaceholderLeague =
    currentLeague?.name?.toLowerCase() === "unassigned";

  useEffect(() => {
    if (currentLeague?.id) {
      api.fetchLeagueResults(currentLeague.id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentLeague?.id]);

  useEffect(() => {
    if (currentLeague?.game) {
      api.fetchRewardMeta(currentLeague.game);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentLeague?.game]);

  useEffect(() => {
    let active = true;
    setRoster(null);
    if (!currentLeague?.id || isPlaceholderLeague) return undefined;
    (async () => {
      const result = await getClassroomProgress(currentLeague.id);
      if (!active) return;
      setRoster(
        result.success ? (result.data.teams || []).map((team) => team.name) : null
      );
    })();
    return () => {
      active = false;
    };
  }, [currentLeague?.id, isPlaceholderLeague, getClassroomProgress]);

  const hasResults = allSimulations && allSimulations.length > 0;

  return (
    <div className="space-y-6">
      <SimulationRunner league={currentLeague} userRole={userRole} />

      {isPlaceholderLeague ? (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex flex-col items-center justify-center p-8 bg-ui-lighter rounded-lg">
            <p className="text-ui-dark text-lg">
              {`The "unassigned" ${T.league} is a placeholder for ${T.teams} without a ${T.league}.`}
            </p>
            <p className="text-ui mt-2">
              It has no game, so simulations cannot be run on it.
            </p>
          </div>
        </div>
      ) : hasResults ? (
        <>
          <SimulationRunSummary
            simulations={allSimulations}
            current={currentSimulation}
            onSelect={(timestamp) => dispatch(setCurrentSimulation(timestamp))}
            league={currentLeague}
            userRole={userRole}
            roster={roster}
          />

          {currentSimulation && (
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-semibold text-ui-dark mb-4">
                Leaderboard
              </h2>
              <ResultsDisplay
                data={currentSimulation}
                highlight={false}
                data_message={currentSimulation.message}
                tablevisible={!currentSimulation.feedback}
              />
            </div>
          )}

          {currentSimulation?.feedback && (
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-semibold text-ui-dark mb-1">
                {`Feedback shown to ${T.teams}`}
              </h2>
              <p className="text-sm text-ui mb-4">
                {`Published with this run — ${T.teams} see it on the results page.`}
              </p>
              <FeedbackSelector
                feedback={currentSimulation.feedback}
                collapsible={false}
              />
            </div>
          )}
        </>
      ) : (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex flex-col items-center justify-center p-8 bg-ui-lighter rounded-lg">
            <p className="text-ui-dark text-lg">
              {`No simulation results yet for this ${T.league}.`}
            </p>
            <p className="text-ui mt-2">
              Use Run Simulation above — the first result appears here.
            </p>
          </div>
        </div>
      )}

      {/* Custom Rewards (hidden when game has no schema) */}
      {!isPlaceholderLeague && <CustomRewards />}
    </div>
  );
};

export default SimulationPanel;
