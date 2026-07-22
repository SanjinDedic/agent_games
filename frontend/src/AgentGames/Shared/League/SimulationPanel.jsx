// src/AgentGames/Shared/League/SimulationPanel.jsx
import React, { useEffect } from 'react';
import { toast } from 'react-toastify';
import { useSelector, useDispatch } from 'react-redux';

import { setCurrentSimulation } from "../../../slices/leaguesSlice";

import SimulationRunner from "./SimulationRunner";
import LeaguePublish from "./LeaguePublish";
import CustomRewards from "../Common/CustomRewards";
import ResultsDisplay from "../Utilities/ResultsDisplay";
import FeedbackSelector from "../../Feedback/FeedbackSelector";

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

  const handleTableDropdownChange = (event) => {
    dispatch(setCurrentSimulation(event.target.value));
  };

  const renderPublishedResults = () => {
    const publishedResults = allSimulations.filter((sim) => sim.publish_link);

    if (publishedResults.length === 0) {
      return null;
    }

    return (
      <div className="mt-6 border-t pt-4 border-ui-light">
        <h3 className="text-lg font-semibold text-ui-dark mb-2">
          Published Results
        </h3>
        <div className="space-y-2">
          {publishedResults.map((result, index) => {
            const baseUrl = `${window.location.protocol}//${window.location.host}`;
            const resultsUrl = `/results/${result.publish_link}`;
            const fullUrl = `${baseUrl}${resultsUrl}`;

            return (
              <div
                key={index}
                className="flex items-center justify-between bg-ui-lighter p-3 rounded-lg"
              >
                <div className="text-sm">
                  <span className="font-medium">
                    {new Date(result.timestamp).toLocaleString()}
                  </span>
                  <span className="ml-2 text-ui">
                    ({result.num_simulations} simulations)
                  </span>
                </div>
                <div className="flex items-center">
                  <a
                    href={resultsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:text-primary-hover text-sm mr-2"
                  >
                    View
                  </a>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(fullUrl);
                      toast.success("Link copied to clipboard!");
                    }}
                    className="p-1.5 bg-primary hover:bg-primary-hover text-white rounded text-xs"
                  >
                    Copy Link
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* Left Column - Controls */}
      <div className="space-y-4">
        <SimulationRunner league={currentLeague} userRole={userRole} />

        {/* Publish Button */}
        {currentLeague && currentSimulation && !isPlaceholderLeague && (
          <div className="bg-white rounded-lg shadow-lg p-4">
            <LeaguePublish
              simulation_id={currentSimulation.id}
              selected_league_id={currentLeague.id}
              selected_league_name={currentLeague.name}
              userRole={userRole}
            />
          </div>
        )}
      </div>

      {/* Right Column - Results */}
      <div className="lg:col-span-3 space-y-6">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold text-ui-dark mb-4">
            Simulation Results
          </h2>

          {isPlaceholderLeague ? (
            <div className="flex flex-col items-center justify-center p-8 bg-ui-lighter rounded-lg">
              <p className="text-ui-dark text-lg">
                {`The "unassigned" ${T.league} is a placeholder for ${T.teams} without a ${T.league}.`}
              </p>
              <p className="text-ui mt-2">
                It has no game, so simulations cannot be run on it.
              </p>
            </div>
          ) : allSimulations && allSimulations.length > 0 ? (
            <>
              <select
                onChange={handleTableDropdownChange}
                className="w-full p-3 mb-4 border border-ui-light rounded-lg bg-white text-ui-dark text-lg shadow-sm focus:ring-2 focus:ring-primary focus:border-primary transition-all"
              >
                {allSimulations.map((option, index) => (
                  <option key={index} value={option.timestamp}>
                    {new Date(option.timestamp).toLocaleString()}
                    {option.publish_link ? " (Published)" : ""}
                  </option>
                ))}
              </select>

              {/* Results Display */}
              {currentSimulation && (
                <>
                  <ResultsDisplay
                    data={currentSimulation}
                    highlight={false}
                    data_message={currentSimulation.message}
                    tablevisible={!currentSimulation.feedback}
                  />
                  {currentSimulation.feedback && (
                    <div className="mt-6">
                      <FeedbackSelector
                        feedback={currentSimulation.feedback}
                      />
                    </div>
                  )}
                </>
              )}

              {/* Published Results List */}
              {renderPublishedResults()}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center p-8 bg-ui-lighter rounded-lg">
              <p className="text-ui-dark text-lg">
                {`No simulation results found for this ${T.league}.`}
              </p>
              <p className="text-ui mt-2">
                Run a simulation using the simulation controls.
              </p>
            </div>
          )}
        </div>

        {/* Custom Rewards (hidden when game has no schema) */}
        {!isPlaceholderLeague && <CustomRewards />}
      </div>
    </div>
  );
};

export default SimulationPanel;
