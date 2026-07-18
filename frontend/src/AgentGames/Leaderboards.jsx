import React, { useState, useEffect, useMemo } from "react";
import { toast } from "react-toastify";
import { Link } from "react-router-dom";
import moment from "moment-timezone";
import { useDispatch, useSelector } from "react-redux";
import { fetchAllRankings, fetchMyLeagueRankings } from "../slices/rankingsSlice";
import { selectCurrentUser } from "../slices/authSlice";
import useLeagueAPI from "./Shared/hooks/useLeagueAPI";
import PureMarkdown from "./Shared/Utilities/PureMarkdown";
import { useTerms } from "./Shared/terminology";

function Leaderboards() {
  const T = useTerms();
  const dispatch = useDispatch();
  const publishedResults = useSelector((state) => state.rankings.allRankings);
  const myLeagueResults = useSelector(
    (state) => state.rankings.myLeagueRankings
  );
  const myLeagueNameCached = useSelector(
    (state) => state.rankings.myLeagueName
  );
  const myLeagueInfoMarkdownCached = useSelector(
    (state) => state.rankings.myLeagueInfoMarkdown
  );
  const leaguesList = useSelector((state) => state.leagues.list);
  const currentUser = useSelector(selectCurrentUser);

  const isTeamUser =
    !!currentUser?.league_id &&
    (currentUser?.role === "student" || currentUser?.role === "ai_agent");

  const { fetchUserLeagues } = useLeagueAPI();

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedLeague, setSelectedLeague] = useState("all");
  const [selectedResultId, setSelectedResultId] = useState(null);

  // Resolve the team's league record (for league name + info_markdown).
  const myLeague = useMemo(() => {
    if (!isTeamUser) return null;
    return leaguesList.find((l) => l.id === currentUser.league_id) || null;
  }, [isTeamUser, leaguesList, currentUser?.league_id]);

  const myLeagueName = myLeague?.name ?? myLeagueNameCached;
  const myLeagueMarkdown =
    myLeague?.info_markdown ?? myLeagueInfoMarkdownCached ?? "";

  const leagues = useMemo(
    () => [...new Set(publishedResults.map((r) => r.league_name))],
    [publishedResults]
  );

  const loadPublicResults = async (force = false) => {
    setIsLoading(true);
    setError(null);
    const res = await dispatch(fetchAllRankings({ force }));
    if (!res.success) {
      setError(res.error || "Failed to fetch published results");
      toast.error(res.error || "Failed to fetch published results");
    }
    setIsLoading(false);
  };

  const loadMyLeagueResults = async (force = false) => {
    setIsLoading(true);
    setError(null);
    const res = await dispatch(fetchMyLeagueRankings({ force }));
    if (!res.success) {
      setError(res.error || "Failed to fetch published results");
      toast.error(res.error || "Failed to fetch published results");
    }
    setIsLoading(false);
  };

  // Team mode: fetch leagues (for league name + markdown) and league-scoped results.
  // `info_markdown` is served by /get-all-published-results-for-my-league and is
  // persisted in sessionStorage via the rankings slice. A plain mount-time fetch
  // is short-circuited by the cache, so admin edits to league info don't surface
  // until the team user clears their session. Force a refresh on every mount.
  useEffect(() => {
    if (isTeamUser) {
      if (leaguesList.length === 0) {
        fetchUserLeagues();
      }
      loadMyLeagueResults(true);
    } else {
      loadPublicResults();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isTeamUser]);

  // Default the dropdown selection to the latest result.
  useEffect(() => {
    if (!isTeamUser) return;
    if (myLeagueResults.length === 0) {
      setSelectedResultId(null);
      return;
    }
    const stillExists = myLeagueResults.some(
      (r) => r.id === selectedResultId
    );
    if (!stillExists) {
      setSelectedResultId(myLeagueResults[0].id);
    }
  }, [isTeamUser, myLeagueResults, selectedResultId]);

  const fetchPublishedResults = () =>
    isTeamUser ? loadMyLeagueResults(true) : loadPublicResults(true);

  if (isTeamUser) {
    const selectedResult =
      myLeagueResults.find((r) => r.id === selectedResultId) ||
      myLeagueResults[0] ||
      null;

    return (
      <div className="min-h-screen pt-20 pb-8 bg-ui-lighter">
        <div className="container mx-auto px-4">
          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h1 className="text-2xl font-bold text-ui-dark">
              Welcome {currentUser.name},
              {myLeagueName ? (
                <>
                  {" "}you are enrolled in{" "}
                  <span className="text-primary">{myLeagueName}</span>.
                </>
              ) : (
                <>{` you are enrolled in your ${T.league}.`}</>
              )}
            </h1>
            <p className="text-ui-dark mt-1">
              {`Here is the key information for your ${T.league}.`}
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 className="text-xl font-semibold text-ui-dark mb-2">
              {`${T.League} Info`}
            </h2>
            {myLeagueMarkdown && myLeagueMarkdown.trim() ? (
              <PureMarkdown content={myLeagueMarkdown} />
            ) : (
              <p className="text-ui">
                {`No info has been posted for this ${T.league} yet.`}
              </p>
            )}
          </div>

          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex justify-between items-center mb-6 flex-wrap gap-3">
              <h2 className="text-xl font-bold text-ui-dark">
                Published Results
              </h2>
              <div className="flex items-center gap-3">
                <label htmlFor="my-result-picker" className="text-ui-dark">
                  Result:
                </label>
                <select
                  id="my-result-picker"
                  value={selectedResultId ?? ""}
                  onChange={(e) =>
                    setSelectedResultId(Number(e.target.value) || null)
                  }
                  className="p-2 border border-ui-light rounded-lg"
                  disabled={myLeagueResults.length === 0}
                >
                  {myLeagueResults.length === 0 && (
                    <option value="">No results</option>
                  )}
                  {myLeagueResults.map((r) => (
                    <option key={r.id} value={r.id}>
                      {moment(r.timestamp).format("MMMM D, YYYY h:mm A")} (#
                      {r.id})
                    </option>
                  ))}
                </select>
                <button
                  onClick={fetchPublishedResults}
                  className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg"
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
            ) : !selectedResult ? (
              <div className="text-center py-8">
                <p className="text-ui">
                  {`No published results yet for your ${T.league}.`}
                </p>
              </div>
            ) : (
              <div className="border border-ui-light rounded-lg overflow-hidden">
                <div className="bg-ui-lighter px-4 py-3 border-b border-ui-light flex justify-between items-center">
                  <div>
                    <p className="text-sm text-ui">
                      Published on:{" "}
                      {moment(selectedResult.timestamp).format(
                        "MMMM D, YYYY h:mm A"
                      )}
                    </p>
                    <p className="text-sm text-ui">
                      Result ID: #{selectedResult.id}
                    </p>
                  </div>
                  {selectedResult.publish_link && (
                    <Link
                      to={`/results/${selectedResult.publish_link}`}
                      className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg"
                    >
                      View Results
                    </Link>
                  )}
                </div>
                <div className="p-4">
                  <div className="mb-4">
                    <p className="text-ui-dark">
                      <strong>Simulations:</strong>{" "}
                      {selectedResult.num_simulations}
                    </p>
                  </div>

                  <h3 className="font-medium text-ui-dark mb-2">{`Top ${T.Teams}:`}</h3>
                  <div className="overflow-x-auto">
                    <table className="min-w-full">
                      <thead>
                        <tr className="bg-ui-lighter">
                          <th className="px-4 py-2 text-left text-ui-dark">
                            Rank
                          </th>
                          <th className="px-4 py-2 text-left text-ui-dark">
                            {T.Team}
                          </th>
                          <th className="px-4 py-2 text-left text-ui-dark">
                            Points
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(selectedResult.total_points)
                          .sort((a, b) => b[1] - a[1])
                          .map(([team, points], teamIndex) => {
                            const isMine = team === currentUser.name;
                            return (
                              <tr
                                key={teamIndex}
                                className={
                                  isMine
                                    ? "bg-success-light"
                                    : teamIndex % 2 === 0
                                    ? "bg-white"
                                    : "bg-ui-lighter"
                                }
                              >
                                <td className="px-4 py-2">{teamIndex + 1}</td>
                                <td className="px-4 py-2 font-medium">
                                  {team}
                                  {isMine && (
                                    <span className="ml-2 text-xs text-success">
                                      (you)
                                    </span>
                                  )}
                                </td>
                                <td className="px-4 py-2">{points}</td>
                              </tr>
                            );
                          })}
                      </tbody>
                    </table>
                  </div>

                  {selectedResult.publish_link && (
                    <div className="mt-4 text-center">
                      <Link
                        to={`/results/${selectedResult.publish_link}`}
                        className="text-primary hover:text-primary-hover hover:underline"
                      >
                        View full results and rankings
                      </Link>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ---------- Public (anonymous / non-team) view ----------
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
                {`Filter by ${T.League}:`}
              </label>
              <select
                id="league-filter"
                value={selectedLeague}
                onChange={(e) => setSelectedLeague(e.target.value)}
                className="p-2 border border-ui-light rounded-lg"
              >
                <option value="all">{`All ${T.Leagues}`}</option>
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
                  ? `any ${T.league}`
                  : `the ${T.league} '${selectedLeague}'`}
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
                      {`Top ${T.Teams}:`}
                    </h3>
                    <div className="overflow-x-auto">
                      <table className="min-w-full">
                        <thead>
                          <tr className="bg-ui-lighter">
                            <th className="px-4 py-2 text-left text-ui-dark">
                              Rank
                            </th>
                            <th className="px-4 py-2 text-left text-ui-dark">
                              {T.Team}
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
