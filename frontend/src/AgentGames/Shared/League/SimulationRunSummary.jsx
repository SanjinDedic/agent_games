// src/AgentGames/Shared/League/SimulationRunSummary.jsx
import React, { useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import moment from 'moment-timezone';

import LeaguePublish from './LeaguePublish';
import StatChip from '../Common/StatChip';
import { useTerms } from '../terminology';

/** Placement map {team: rank} for one run, ranked on total points desc. */
const rankMap = (totalPoints) => {
  const map = new Map();
  Object.entries(totalPoints || {})
    .sort((a, b) => b[1] - a[1])
    .forEach(([team], index) => map.set(team, index + 1));
  return map;
};

const runLabel = (run) => {
  const games = (run.num_simulations || 0).toLocaleString();
  const published = run.publish_link ? ' · Published' : '';
  return `${moment(run.timestamp).format('D MMM YYYY, h:mm a')} · ${games} games${published}`;
};

/** ▲n / ▼n / New badge for a team's placement change between two runs. */
const MovementBadge = ({ team, delta }) => {
  if (delta === null) {
    return (
      <span className="px-2 py-1 rounded bg-primary-light/20 text-primary-dark text-sm">
        {team} <span className="font-semibold">New</span>
      </span>
    );
  }
  if (delta === 0) {
    return (
      <span className="px-2 py-1 rounded bg-ui-lighter text-ui text-sm">
        {team} <span className="font-semibold">–</span>
      </span>
    );
  }
  const up = delta > 0;
  return (
    <span
      className={`px-2 py-1 rounded text-sm ${
        up ? 'bg-success-light text-success' : 'bg-danger-light text-danger'
      }`}
    >
      {team}{' '}
      <span className="font-semibold">
        {up ? '▲' : '▼'}
        {Math.abs(delta)}
      </span>
    </span>
  );
};

/**
 * Everything about the *selected* simulation run: which run is shown, publish
 * state, the headline numbers, who was missing from the run, and how placements
 * moved since the previous run. All of it is derived from the run list already
 * in Redux plus (optionally) the classroom roster — no extra run data needed.
 */
const SimulationRunSummary = ({
  simulations,
  current,
  onSelect,
  league,
  userRole,
  roster,
}) => {
  const T = useTerms();
  const [showAllMovement, setShowAllMovement] = useState(false);

  const currentIndex = simulations.findIndex((sim) => sim.id === current?.id);
  // The list is sorted newest first, so the previous run sits one slot later.
  const previous = currentIndex >= 0 ? simulations[currentIndex + 1] : undefined;

  const agentsInRun = Object.keys(current?.total_points || {});

  const movement = useMemo(() => {
    if (!current || !previous) return [];
    const currentRanks = rankMap(current.total_points);
    const previousRanks = rankMap(previous.total_points);
    return [...currentRanks.entries()]
      .map(([team, rank]) => ({
        team,
        rank,
        delta: previousRanks.has(team) ? previousRanks.get(team) - rank : null,
      }))
      .sort((a, b) => a.rank - b.rank);
  }, [current, previous]);

  const movers = useMemo(
    () =>
      [...movement]
        .filter((entry) => entry.delta === null || entry.delta !== 0)
        .sort((a, b) => {
          if (a.delta === null) return -1;
          if (b.delta === null) return 1;
          return Math.abs(b.delta) - Math.abs(a.delta);
        })
        .slice(0, 5),
    [movement]
  );

  const missing = useMemo(() => {
    if (!roster || roster.length === 0 || !current) return [];
    const present = new Set(agentsInRun);
    return roster.filter((name) => !present.has(name));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roster, current]);

  const publishedRuns = simulations.filter((sim) => sim.publish_link);
  const resultsUrl = current?.publish_link ? `/results/${current.publish_link}` : null;
  const fullUrl = resultsUrl
    ? `${window.location.protocol}//${window.location.host}${resultsUrl}`
    : null;

  const copy = (url) => {
    navigator.clipboard.writeText(url);
    toast.success('Link copied to clipboard!');
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 space-y-5">
      {/* Run picker + publish state */}
      <div className="flex flex-col lg:flex-row lg:items-end gap-4">
        <div className="flex-1">
          <label
            htmlFor="simulation-run-picker"
            className="block text-sm font-medium text-ui mb-1"
          >
            Showing run
          </label>
          <select
            id="simulation-run-picker"
            value={current?.timestamp ?? ''}
            onChange={(event) => onSelect(event.target.value)}
            className="w-full p-3 border border-ui-light rounded-lg bg-white text-ui-dark shadow-sm focus:ring-2 focus:ring-primary focus:border-primary transition-all"
          >
            {simulations.map((run) => (
              <option key={run.id} value={run.timestamp}>
                {runLabel(run)}
              </option>
            ))}
          </select>
          <p className="text-xs text-ui mt-1">
            {simulations.length} run{simulations.length !== 1 ? 's' : ''} recorded
            {publishedRuns.length > 0
              ? ` · ${publishedRuns.length} published`
              : ' · none published yet'}
          </p>
        </div>

        <div className="lg:w-80">
          {current?.publish_link ? (
            <div className="p-3 bg-success-light rounded-lg">
              <p className="text-sm font-medium text-success mb-2">
                {`This run is live for your ${T.teams}`}
              </p>
              <div className="flex items-center gap-2">
                <a
                  href={resultsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 p-2 bg-white border border-ui-light rounded-lg text-xs text-primary truncate"
                  title={fullUrl}
                >
                  {fullUrl}
                </a>
                <button
                  onClick={() => copy(fullUrl)}
                  className="p-2 bg-primary hover:bg-primary-hover text-white rounded text-xs"
                >
                  Copy
                </button>
              </div>
            </div>
          ) : (
            current &&
            league && (
              <LeaguePublish
                simulation_id={current.id}
                selected_league_id={league.id}
                selected_league_name={league.name}
                userRole={userRole}
              />
            )
          )}
        </div>
      </div>

      {/* Headline numbers for the selected run */}
      <div className="flex flex-wrap gap-3">
        <StatChip
          label="Games played"
          value={(current?.num_simulations || 0).toLocaleString()}
        />
        <StatChip label="Agents in run" value={agentsInRun.length} />
        <StatChip
          label="Rewards"
          value={current?.rewards ? JSON.stringify(current.rewards) : 'Default'}
        />
        <StatChip
          label="Status"
          value={current?.publish_link ? 'Published' : 'Not published'}
          tone={current?.publish_link ? 'success' : 'plain'}
        />
        {current?.capped && (
          <StatChip
            label="Hit the time cap"
            value={`${(current.num_simulations || 0).toLocaleString()} of ${(
              current.requested_simulations || 0
            ).toLocaleString()} games`}
            tone="warning"
          />
        )}
      </div>

      {/* Who was left out of the run */}
      {roster && roster.length > 0 && (
        <div className="text-sm">
          <span className="text-ui-dark font-medium">
            {roster.length - missing.length} of {roster.length} {T.teams} had an
            agent in this run
          </span>
          {missing.length > 0 && (
            <span className="text-ui">
              {' '}
              — no agent yet: {missing.slice(0, 8).join(', ')}
              {missing.length > 8 ? ` +${missing.length - 8} more` : ''}
            </span>
          )}
        </div>
      )}

      {/* Placement changes since the previous run */}
      {previous && movement.length > 0 && (
        <div className="border-t border-ui-light pt-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2 mb-2">
            <h3 className="text-base font-semibold text-ui-dark">
              Movement since {moment(previous.timestamp).format('D MMM, h:mm a')}
            </h3>
            <button
              onClick={() => setShowAllMovement((v) => !v)}
              className="text-sm text-primary hover:underline"
            >
              {showAllMovement ? 'Show biggest movers only' : `Show all ${T.teams}`}
            </button>
          </div>
          {movers.length === 0 && !showAllMovement ? (
            <p className="text-sm text-ui">
              No placement changes since the previous run.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {(showAllMovement ? movement : movers).map((entry) => (
                <MovementBadge
                  key={entry.team}
                  team={entry.team}
                  delta={entry.delta}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Every published run of this classroom */}
      {publishedRuns.length > 0 && (
        <div className="border-t border-ui-light pt-4">
          <h3 className="text-base font-semibold text-ui-dark mb-2">
            Published links
          </h3>
          <div className="space-y-2">
            {publishedRuns.map((run) => {
              const url = `/results/${run.publish_link}`;
              const absolute = `${window.location.protocol}//${window.location.host}${url}`;
              return (
                <div
                  key={run.id}
                  className="flex items-center justify-between bg-ui-lighter p-3 rounded-lg"
                >
                  <div className="text-sm">
                    <span className="font-medium text-ui-dark">
                      {moment(run.timestamp).format('D MMM YYYY, h:mm a')}
                    </span>
                    <span className="ml-2 text-ui">
                      ({(run.num_simulations || 0).toLocaleString()} games)
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:text-primary-hover text-sm"
                    >
                      View
                    </a>
                    <button
                      onClick={() => copy(absolute)}
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
      )}
    </div>
  );
};

export default SimulationRunSummary;
