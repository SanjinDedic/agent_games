import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import moment from "moment-timezone";

import useTeamAPI from "../Shared/hooks/useTeamAPI";
import { getTerms } from "../Shared/terminology";
import { getGame } from "../Feedback/games";
import { imageUrl } from "../../config/assets";
import { rankTone } from "../Shared/Progress/StatusCell";
import {
  PLACEMENT_STOPS,
  PLACEMENT_TRAILING_STOP,
  stopChip,
  stopInk,
  stopSolid,
} from "../Shared/Progress/progressScale";

// A student who has submitted working code this many times without ever
// beating the bots is grinding, not learning, and gets pointed at the course.
const STUCK_AFTER_VALID_SUBMISSIONS = 10;

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
 * identity, the current league, per-tutorial progress, and agent-game stats.
 * The agent game leads, because it is what students come back for; the
 * tutorials sit under it as the thing to reach for when the agent stalls.
 * Wording follows the owning institution: classroom/student for teacher
 * accounts, league/team for competitions. Unassigned students are sent to
 * the league picker.
 */
function TeamHome() {
  const navigate = useNavigate();
  const { getTeamData } = useTeamAPI();

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

  const T = getTerms(teamData.is_classroom);
  const game = getGame(teamData.league.game);
  const gameDisplayName = game?.displayName || teamData.league.game;
  const stats = teamData.agent_game;
  const tutorials = teamData.tutorials;
  const showTutorials = tutorials.length > 0 || teamData.is_classroom;

  const validSubmissions = stats?.validated_submissions ?? 0;
  const failedAttempts = (stats?.total_attempts ?? 0) - validSubmissions;

  // Beating the bots means first place; anything less has not won yet.
  const stuck =
    !stats?.achieved_first && validSubmissions > STUCK_AFTER_VALID_SUBMISSIONS;
  // The unfinished course with the most left to gain. A student who has
  // finished everything gets no nudge — there is nowhere to send them.
  const nudgeTutorial = tutorials
    .filter((tutorial) => tutorial.passed_count < tutorial.exercise_count)
    .sort(
      (a, b) =>
        a.passed_count / (a.exercise_count || 1) -
        b.passed_count / (b.exercise_count || 1)
    )[0];
  const showNudge = stuck && Boolean(nudgeTutorial);

  return (
    <div className="min-h-screen pt-16 pb-12 bg-ui-lighter">
      <div className="max-w-4xl mx-auto px-4">
        {/* Welcome header */}
        <div className="bg-white rounded-lg shadow border border-ui-light/30 p-6">
          <p className="text-sm uppercase tracking-wide text-ui-dark/60">
            {teamData.institution_name || "Agent Games"}
          </p>
          <h1 className="text-2xl font-bold text-ui-dark mt-1">
            Welcome back, {teamData.team_name}
          </h1>
          <p className="mt-2 text-ui-dark/70">
            {teamData.is_classroom
              ? `You're in the ${teamData.league.name} ${T.league}. Build your ${gameDisplayName} agent, and use your ${T.tutorials} whenever you need the Python behind it.`
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

                {showNudge && (
                  <div className="mt-4 flex gap-3 rounded-lg border border-ui-light bg-ui-lighter p-4">
                    <span
                      className={`w-1.5 self-stretch rounded-full flex-shrink-0 ${stopSolid(
                        PLACEMENT_TRAILING_STOP
                      )}`}
                      aria-hidden="true"
                    />
                    <div className="min-w-0">
                      <p
                        className={`font-semibold ${stopInk(
                          PLACEMENT_TRAILING_STOP
                        )}`}
                      >
                        Stuck on {gameDisplayName}?
                      </p>
                      <p className="mt-1 text-sm text-ui-dark/70">
                        {validSubmissions} valid submissions and no 1st place
                        yet. {nudgeTutorial.title} covers the Python you need —
                        you're {nudgeTutorial.passed_count} of{" "}
                        {nudgeTutorial.exercise_count} through it.
                      </p>
                      <button
                        onClick={() =>
                          navigate(`/Tutorial?tutorial=${nudgeTutorial.id}`)
                        }
                        className="mt-3 py-2 px-4 font-medium text-white bg-primary hover:bg-primary-hover rounded-lg transition-colors duration-200"
                      >
                        Continue your {T.tutorial} →
                      </button>
                    </div>
                  </div>
                )}

                <div className="mt-5 flex flex-col sm:flex-row gap-3">
                  <Link
                    to="/AgentSubmission"
                    className="text-center py-2.5 px-5 text-lg font-medium text-white bg-primary hover:bg-primary-hover rounded-lg transition-colors duration-200"
                  >
                    Open Agent Workspace
                  </Link>
                  {!teamData.is_demo && (
                    <Link
                      to="/Leaderboards"
                      className="text-center py-2.5 px-5 text-lg font-medium text-ui-dark bg-ui-lighter hover:bg-ui-light rounded-lg transition-colors duration-200"
                    >
                      Leaderboards
                    </Link>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Tutorials */}
        {showTutorials && (
          <section className="mt-8">
            <h2 className="text-xl font-bold text-ui-dark mb-1">{T.Tutorials}</h2>
            <p className="text-ui-dark/60 mb-4">
              {teamData.is_classroom
                ? `Guided Python exercises set up for your ${T.league}.`
                : `Practice exercises available to your ${T.league}.`}
            </p>
            {tutorials.length === 0 ? (
              <div className="bg-white rounded-lg shadow border border-ui-light/30 p-6 text-ui-dark/60">
                {`Your teacher hasn't added any ${T.tutorials} yet — check back soon.`}
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {tutorials.map((tutorial) => {
                  const percent =
                    tutorial.exercise_count > 0
                      ? Math.round(
                          (tutorial.passed_count / tutorial.exercise_count) * 100
                        )
                      : 0;
                  return (
                    <button
                      key={tutorial.id}
                      onClick={() => navigate(`/Tutorial?tutorial=${tutorial.id}`)}
                      className="bg-white rounded-lg shadow border border-ui-light/30 p-5 text-left transition-colors hover:border-primary/60 hover:bg-primary/5"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <span className="font-semibold text-ui-dark">
                          {tutorial.title}
                        </span>
                        {percent === 100 && (
                          <span className="flex-shrink-0 text-xs font-bold text-white bg-success rounded-full px-2 py-1">
                            DONE
                          </span>
                        )}
                      </div>
                      {tutorial.description && (
                        <p className="mt-1 text-sm text-ui-dark/60 line-clamp-2">
                          {tutorial.description}
                        </p>
                      )}
                      <div className="mt-4">
                        <div className="flex justify-between text-sm text-ui-dark/70 mb-1">
                          <span>
                            {tutorial.passed_count} of {tutorial.exercise_count}{" "}
                            exercises completed
                          </span>
                          <span>{percent}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-ui-lighter overflow-hidden">
                          <div
                            className="h-full rounded-full bg-success transition-all duration-400"
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}

export default TeamHome;
