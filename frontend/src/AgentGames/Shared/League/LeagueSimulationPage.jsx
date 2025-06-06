// src/AgentGames/Shared/League/LeagueSimulationPage.jsx
import React, { useEffect } from 'react';
import { toast } from 'react-toastify';
import { useSelector, useDispatch } from 'react-redux';
import moment from 'moment-timezone';
import { useNavigate } from 'react-router-dom';

// Import Redux actions
import {
  setLeagues,
  setCurrentSimulation,
  setResults,
  clearResults,
} from "../../../slices/leaguesSlice";

// Import components
import LeagueCardList from "./LeagueCardList";
import SimulationRunner from "./SimulationRunner";
import LeaguePublish from "./LeaguePublish";
import CustomRewards from "../Common/CustomRewards";
import ResultsDisplay from "../Utilities/ResultsDisplay";
import FeedbackSelector from "../../Feedback/FeedbackSelector";

// Import hooks
import useLeagueAPI from "../hooks/useLeagueAPI";

const LeagueSimulationPage = ({ userRole, redirectPath, onUnauthorized }) => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const currentLeague = useSelector((state) => state.leagues.currentLeague);
  const allSimulations = useSelector(
    (state) => state.leagues.currentLeagueResults
  );
  const currentSimulation = useSelector(
    (state) => state.leagues.currentLeagueResultSelected
  );

  // Use the shared API hook
  const api = useLeagueAPI(userRole);

  moment.tz.setDefault("Australia/Sydney");

  useEffect(() => {
    fetchLeagues();
  }, []);

  useEffect(() => {
    if (currentLeague?.name) {
      fetchLeagueResults();
    }
  }, [currentLeague]);

  // Fetch all leagues
  const fetchLeagues = async () => {
    try {
      const response = await fetch(`${apiUrl}/user/get-all-leagues`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      const data = await response.json();

      if (data.status === "success") {
        dispatch(setLeagues(data.data.leagues));
      } else if (data.status === "failed") {
        toast.error(data.message);
      } else if (data.detail === "Invalid token") {
        onUnauthorized();
      }
    } catch (error) {
      console.error("Error fetching leagues:", error);
    }
  };

  // Fetch league results
  const fetchLeagueResults = async () => {
    try {
      const response = await fetch(
        `${apiUrl}/institution/get-all-league-results`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({ name: currentLeague.name }),
        }
      );

      const data = await response.json();

      if (data.status === "success") {
        if (data.data.results.length === 0) {
          dispatch(clearResults());
          toast.info("No results in the selected League");
        } else {
          dispatch(setResults(data.data.results));
        }
      } else if (data.status === "failed") {
        toast.error(data.message);
        dispatch(clearResults());
      } else if (data.detail === "Invalid token") {
        onUnauthorized();
      }
    } catch (error) {
      console.error("Error fetching league results:", error);
    }
  };

  // Handle simulation selection change
  const handleTableDropdownChange = (event) => {
    dispatch(setCurrentSimulation(event.target.value));
  };

  // Navigate to the league management page
  const handleGoToManagement = () => {
    const path = userRole === "admin" ? "/AdminLeague" : "/InstitutionLeague";
    navigate(path);
  };

  // Render published results with links
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
    <div className="min-h-screen bg-ui-lighter">
      <div className="max-w-[1800px] mx-auto px-6 pt-20 pb-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-ui-dark mb-4">
              League Simulation & Results
            </h1>
            <button
              onClick={handleGoToManagement}
              className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg transition-colors"
            >
              Go to League Management
            </button>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left Column - Controls (1/4 width) */}
          <div className="space-y-4">
            {/* League Selection */}
            <div className="bg-white rounded-lg shadow-lg p-4">
              <h2 className="text-xl font-semibold text-ui-dark mb-4">
                Select League
              </h2>
              <LeagueCardList userRole={userRole} />
            </div>

            {/* Simulation Controls */}
            <SimulationRunner league={currentLeague} userRole={userRole} />

            {/* Custom Rewards */}
            <CustomRewards />

            {/* Publish Button */}
            {currentLeague && currentSimulation && (
              <div className="bg-white rounded-lg shadow-lg p-4">
                <LeaguePublish
                  simulation_id={currentSimulation.id}
                  selected_league_name={currentLeague.name}
                  userRole={userRole}
                />
              </div>
            )}
          </div>

          {/* Right Column - Results (3/4 width) */}
          <div className="lg:col-span-3 space-y-6">
            {/* Results Selection */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-semibold text-ui-dark mb-4">
                Simulation Results
              </h2>

              {allSimulations && allSimulations.length > 0 ? (
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
                    No simulation results found for this league.
                  </p>
                  <p className="text-ui mt-2">
                    Run a simulation using the controls on the left.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LeagueSimulationPage;