import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useSelector } from "react-redux";
import moment from "moment-timezone";

import useTeamAPI from "../Shared/hooks/useTeamAPI";
import { selectSiteName } from "../../slices/settingsSlice";
import { useTerms } from "../Shared/terminology";
import { getGame } from "../Feedback/games";
import { imageUrl } from "../../config/assets";
import { rankTone } from "../Shared/Progress/StatusCell";
import { PLACEMENT_STOPS, stopChip } from "../Shared/Progress/progressScale";

const ordinal = (n) => {
  const rem10 = n % 10;
  const rem100 = n % 100;
  if (rem10 === 1 && rem100 !== 11) return `${n}st`;
  if (rem10 === 2 && rem100 !== 12) return `${n}nd`;
  if (rem10 === 3 && rem100 !== 13) return `${n}rd`;
  return `${n}th`;
};

function StatTile({ label, value, children }) {
  return (
    <div className="bg-ui-lighter rounded-lg p-4 text-center">
      <div className="h-9 flex items-center justify-center gap-1.5 text-2xl font-bold text-ui-dark">
        {children ?? value}
      </div>
      <div className="text-sm text-ui-dark/60 mt-1">{label}</div>
    </div>
  );
}

/**
 * One validation placement, on the same ramp the teacher's submissions grid
 * colours by — so a student and their teacher read the same number in the
 * same colour.
 */
function PlacementSquare({ ranking }) {
  return (
    <span
      title={`${ordinal(ranking)} against the validation bots`}
      className={`inline-flex w-9 h-9 items-center justify-center rounded-md text-base font-mono font-bold ${rankTone(
        ranking
      )}`}
    >
      {ranking}
    </span>
  );
}

/**
 * Student landing page. One backend call (GET /user/team-data) provides
 * identity, the current league, and agent-game stats.
 * Wording follows SITE_MODE: classroom/student for a classroom
 * accounts, league/team for competitions. Unassigned students are sent to
 * the league picker.
 */
function TeamHome() {
  const navigate = useNavigate();
  const { getTeamData } = useTeamAPI();
  // Every hook lives above the loading/error early returns: called after them,
  // the loaded render runs more hooks than the loading one did and React tears
  // the page down with "Rendered more hooks than during the previous render".
  const T = useTerms();
  const siteName = useSelector(selectSiteName);

  const [teamData, setTeamData] = useState(null);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const result = await getTeamData();
      if (cancelled) return;
      if (result.success) {
        setTeamData(result.data);
      } else {
        setLoadError(result.error);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [getTeamData]);

  // No real league yet: the picker is the useful landing page.
  useEffect(() => {
    if (teamData && !teamData.league) {
      navigate("/AgentLeagueSignUp", { replace: true });
    }
  }, [teamData, navigate]);

  if (loadError) {
    return (
      <div className="min-h-screen pt-12 flex items-center justify-center bg-ui-lighter">
        <div className="text-center p-8 text-ui">
          <p className="text-xl">{loadError}</p>
          <p className="text-sm mt-2">Please try again later.</p>
        </div>
      </div>
    );
  }

  if (!teamData || !teamData.league) {
    return (
      <div className="min-h-screen pt-12 flex items-center justify-center bg-ui-lighter">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
        <span className="ml-3 text-ui-dark">Loading your home page...</span>
      </div>
    );
  }

  const game = getGame(teamData.league.game);
  const gameDisplayName = game?.displayName || teamData.league.game;
  const stats = teamData.agent_game;
  const validSubmissions = stats?.validated_submissions ?? 0;
  const failedAttempts = (stats?.total_attempts ?? 0) - validSubmissions;

  return (
    <div className="min-h-screen pt-16 pb-12 bg-ui-lighter">
      <div className="max-w-4xl mx-auto px-4">
        {/* Welcome header */}
        <div className="bg-white rounded-lg shadow border border-ui-light/30 p-6">
          <p className="text-sm uppercase tracking-wide text-ui-dark/60">
            {siteName}
          </p>
          <h1 className="text-2xl font-bold text-ui-dark mt-1">
            Welcome back, {teamData.team_name}
          </h1>
          <p className="mt-2 text-ui-dark/70">
            {teamData.is_classroom
              ? `You're in the ${teamData.league.name} ${T.league}. Build your ${gameDisplayName} agent and see how it fares.`
              : `You're competing in ${teamData.league.name}. Keep improving your ${gameDisplayName} agent to climb the rankings.`}
          </p>
        </div>

        {/* Agent game */}
        <section className="mt-8">
          <h2 className="text-xl font-bold text-ui-dark mb-1">Agent Game</h2>
          <p className="text-ui-dark/60 mb-4">
            {teamData.is_classroom
              ? "Your coding challenge: build an agent that plays for you."
              : "Your competition game: build the smartest agent in the field."}
          </p>
          <div className="bg-white rounded-lg shadow border border-ui-light/30 overflow-hidden">
            <div className="flex flex-col sm:flex-row">
              {game?.thumbnail && (
                <img
                  src={imageUrl(game.thumbnail)}
                  alt={`${gameDisplayName} game`}
                  className="w-full sm:w-56 h-40 sm:h-auto object-cover"
                />
              )}
              <div className="flex-1 p-6">
                <div className="flex items-center gap-3 flex-wrap">
                  <h3 className="text-2xl font-bold text-ui-dark">
                    {gameDisplayName}
                  </h3>
                  {stats?.achieved_first && (
                    <span
                      className={`text-xs font-bold border rounded-full px-2 py-1 ${stopChip(
                        PLACEMENT_STOPS[1]
                      )}`}
                    >
                      🏆 REACHED 1ST
                    </span>
                  )}
                </div>
                {game?.shortDescription && (
                  <p className="mt-1 text-ui-dark/60">{game.shortDescription}</p>
                )}

                <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <StatTile label="Best placement">
                    {stats?.best_ranking ? (
                      <>
                        <PlacementSquare ranking={stats.best_ranking} />
                        {stats.field_size && (
                          <span className="text-base font-medium text-ui-dark/50">
                            of {stats.field_size}
                          </span>
                        )}
                      </>
                    ) : (
                      "—"
                    )}
                  </StatTile>
                  <StatTile label="Recent placements">
                    {stats?.recent_rankings?.length
                      ? stats.recent_rankings.map((ranking, i) => (
                          <PlacementSquare key={i} ranking={ranking} />
                        ))
                      : "—"}
                  </StatTile>
                  <StatTile
                    label="Valid submissions"
                    value={validSubmissions}
                  />
                </div>
                <p className="mt-3 text-sm text-ui-dark/50">
                  {stats?.latest_submission
                    ? `Last submission ${moment(stats.latest_submission).fromNow()}`
                    : "No submissions yet — open the workspace to write your first agent."}
                  {failedAttempts > 0 &&
                    ` · ${failedAttempts} attempt${
                      failedAttempts === 1 ? "" : "s"
                    } didn't get past validation`}
                </p>

                <div className="mt-5 flex flex-col sm:flex-row gap-3">
                  <Link
                    to="/AgentSubmission"
                    className="text-center py-2.5 px-5 text-lg font-medium text-white bg-primary hover:bg-primary-hover rounded-lg transition-colors duration-200"
                  >
                    Open Agent Workspace
                  </Link>
                  <Link
                    to="/Leaderboards"
                    className="text-center py-2.5 px-5 text-lg font-medium text-ui-dark bg-ui-lighter hover:bg-ui-light rounded-lg transition-colors duration-200"
                  >
                    Leaderboards
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}

export default TeamHome;
