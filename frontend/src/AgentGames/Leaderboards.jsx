import React, { useState, useEffect } from "react";
import { toast } from "react-toastify";
import { Link } from "react-router-dom";
import moment from "moment-timezone";

function Leaderboards() {
  const [publishedResults, setPublishedResults] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedLeague, setSelectedLeague] = useState("all");
  const [leagues, setLeagues] = useState([]);

  // Get API URL from environment
  const apiUrl = process.env.REACT_APP_AGENT_API_URL;

  useEffect(() => {
    fetchPublishedResults();
  }, []);

  const fetchPublishedResults = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(
        `${apiUrl}/user/get-published-results-for-all-leagues`
      );
      const data = await response.json();

      if (data.status === "success") {
        const results = data.data.all_results || [];
        setPublishedResults(results);

        // Extract unique league names for the filter dropdown
        const uniqueLeagues = [
          ...new Set(results.map((result) => result.league_name)),
        ];
        setLeagues(uniqueLeagues);
      } else {
        setError(data.message || "Failed to fetch published results");
        toast.error(data.message || "Failed to fetch published results");
      }
    } catch (error) {
      console.error("Error fetching published results:", error);
      setError("Error connecting to server");
      toast.error("Error connecting to server");
    } finally {
      setIsLoading(false);
    }
  };

  // Filter results by selected league
  const filteredResults =
    selectedLeague === "all"
      ? publishedResults
      : publishedResults.filter(
          (result) => result.league_name === selectedLeague
        );

  return (
    <div className="min-h-screen pt-20 pb-8 bg-ui-lighter">
      <div className="container mx-auto px-4">
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold text-ui-dark">
              Published Results
            </h1>
            <div className="flex items-center">
              <label htmlFor="league-filter" className="mr-2 text-ui-dark">
                Filter by League:
              </label>
              <select
                id="league-filter"
                value={selectedLeague}
                onChange={(e) => setSelectedLeague(e.target.value)}
                className="p-2 border border-ui-light rounded-lg"
              >
                <option value="all">All Leagues</option>
                {leagues.map((league, index) => (
                  <option key={index} value={league}>
                    {league}
                  </option>
                ))}
              </select>

              <button
                onClick={fetchPublishedResults}
                className="ml-4 px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg"
                disabled={isLoading}
              >
                {isLoading ? "Refreshing..." : "Refresh"}
              </button>
            </div>
          </div>

          {isLoading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
            </div>
          ) : error ? (
            <div className="bg-danger-light text-danger p-6 rounded-lg text-center">
              <p>{error}</p>
            </div>
          ) : filteredResults.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-ui">
                No published results found for{" "}
                {selectedLeague === "all"
                  ? "any league"
                  : `the league '${selectedLeague}'`}
                .
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredResults.map((result, index) => (
                <div
                  key={index}
                  className="border border-ui-light rounded-lg overflow-hidden"
                >
                  <div className="bg-ui-lighter px-4 py-3 border-b border-ui-light flex justify-between items-center">
                    <div>
                      <h2 className="text-lg font-semibold text-ui-dark">
                        {result.league_name}
                        <span className="ml-2 text-sm font-normal text-ui">
                          ({result.game})
                        </span>
                      </h2>
                      <p className="text-sm text-ui">
                        Published on:{" "}
                        {moment(result.timestamp).format("MMMM D, YYYY h:mm A")}
                      </p>
                    </div>
                    <Link
                      to={`/results/${result.publish_link}`}
                      className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg"
                    >
                      View Results
                    </Link>
                  </div>
                  <div className="p-4">
                    <div className="mb-4">
                      <p className="text-ui-dark">
                        <strong>Simulations:</strong> {result.num_simulations}
                      </p>
                    </div>

                    <h3 className="font-medium text-ui-dark mb-2">
                      Top Teams:
                    </h3>
                    <div className="overflow-x-auto">
                      <table className="min-w-full">
                        <thead>
                          <tr className="bg-ui-lighter">
                            <th className="px-4 py-2 text-left text-ui-dark">
                              Rank
                            </th>
                            <th className="px-4 py-2 text-left text-ui-dark">
                              Team
                            </th>
                            <th className="px-4 py-2 text-left text-ui-dark">
                              Points
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(result.total_points)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 5) // Show top 5 teams
                            .map(([team, points], teamIndex) => (
                              <tr
                                key={teamIndex}
                                className={
                                  teamIndex % 2 === 0
                                    ? "bg-white"
                                    : "bg-ui-lighter"
                                }
                              >
                                <td className="px-4 py-2">{teamIndex + 1}</td>
                                <td className="px-4 py-2 font-medium">
                                  {team}
                                </td>
                                <td className="px-4 py-2">{points}</td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="mt-4 text-center">
                      <Link
                        to={`/results/${result.publish_link}`}
                        className="text-primary hover:text-primary-hover hover:underline"
                      >
                        View full results and rankings
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Leaderboards;
