import React, { useEffect, useMemo, useState } from 'react';

import useClassroomAPI from '../../Shared/hooks/useClassroomAPI';
import { useTerms } from '../../Shared/terminology';
import StatusCell, { rankTone } from '../../Shared/Progress/StatusCell';
import {
  formatDuration,
  formatTimestamp,
} from '../../Shared/Submission/CodeHistoryViewer';
import AgentCodeModal from './AgentCodeModal';

// Most teams submit fewer times than this; teams that submit more show only
// their most recent GRID_COLUMNS, with ALL for the complete history.
const GRID_COLUMNS = 15;

/**
 * Agent submissions for the whole classroom at a glance: one row per team,
 * the last 15 submissions as cells showing that submission's placement against
 * the validation bots, coloured dark green (1st) through orange (back of the
 * pack). Clicking a cell opens that submission; ALL opens the full history.
 */
function SubmissionsTab({ league }) {
  const T = useTerms();
  const { getLeagueSubmissions } = useClassroomAPI();

  // submissions: { teamName: [{ code, timestamp, id, duration_ms }, ...] }
  const [submissions, setSubmissions] = useState({});
  const [teamIds, setTeamIds] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  // { teamName, initialIndex } while the code modal is open
  const [modalTarget, setModalTarget] = useState(null);

  const teamList = useMemo(
    () => Object.keys(submissions).sort((a, b) => a.localeCompare(b)),
    [submissions]
  );

  useEffect(() => {
    const fetchSubmissions = async () => {
      if (!league.id) return;
      setLoading(true);
      setError('');
      const result = await getLeagueSubmissions(league.id);
      if (result.success) {
        setSubmissions(result.data.teams || {});
        setTeamIds(result.data.team_ids || {});
      } else {
        setError(result.error);
      }
      setLoading(false);
    };
    fetchSubmissions();
  }, [getLeagueSubmissions, league.id]);

  if (loading) {
    return (
      <div className="p-6 bg-white rounded-lg shadow-lg text-ui">
        Loading submissions…
      </div>
    );
  }
  if (error) {
    return <div className="p-6 bg-white rounded-lg shadow-lg text-danger">{error}</div>;
  }
  if (teamList.length === 0) {
    return (
      <div className="p-6 bg-white rounded-lg shadow-lg text-ui">
        {`No ${T.teams} in this ${T.league} yet.`}
      </div>
    );
  }

  const modalSubmissions = modalTarget
    ? submissions[modalTarget.teamName] || []
    : [];

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 mb-1">
        <h2 className="text-xl font-semibold text-ui-dark">Agent submissions</h2>
        <span className="text-sm text-ui">
          {teamList.length} {teamList.length !== 1 ? T.teams : T.team}
        </span>
      </div>
      <p className="text-sm text-ui mb-4 flex flex-wrap items-center gap-x-2 gap-y-1">
        <span>Each cell is that submission's placement against the validation bots:</span>
        {[1, 2, 3, 4, 5].map((rank) => (
          <span
            key={rank}
            className={`inline-flex w-6 h-6 items-center justify-center rounded text-xs font-mono font-bold ${rankTone(
              rank
            )}`}
          >
            {rank}
          </span>
        ))}
        <span
          className={`inline-flex px-1.5 h-6 items-center justify-center rounded text-xs font-mono font-bold ${rankTone(
            99
          )}`}
        >
          6+
        </span>
        <span>
          <span className="font-bold text-ui-light">·</span> = no submission.
          Click a cell to read it, or ALL to step through the full history.
        </span>
      </p>

      <div className="overflow-x-auto">
        <table className="w-auto">
          <thead>
            <tr className="bg-ui-lighter">
              <th className="px-4 py-2 text-left text-sm font-semibold text-ui-dark sticky left-0 bg-ui-lighter z-10">
                {T.Team}
              </th>
              <th
                colSpan={GRID_COLUMNS}
                className="px-2 py-2 text-center text-sm font-semibold text-ui-dark"
              >
                {`Last ${GRID_COLUMNS} submissions (oldest → newest)`}
              </th>
              <th className="px-3 py-2 text-center text-sm font-semibold text-ui-dark">
                Total
              </th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {teamList.map((team) => {
              const subs = submissions[team] || [];
              const windowed = subs.slice(-GRID_COLUMNS);
              // Empty slots pad the left so the right-most column is always
              // the newest submission, for every team.
              const pad = GRID_COLUMNS - windowed.length;
              const offset = subs.length - windowed.length;

              return (
                <tr
                  key={team}
                  className="border-b border-ui-light hover:bg-ui-lighter/50"
                >
                  <td className="px-4 py-1.5 text-base font-medium text-ui-dark whitespace-nowrap sticky left-0 bg-white z-10">
                    {team}
                  </td>

                  {Array.from({ length: GRID_COLUMNS }, (_, col) => {
                    if (col < pad) {
                      return (
                        <td key={`empty-${col}`} className="px-1 py-1.5 text-center">
                          <StatusCell status="untouched" />
                        </td>
                      );
                    }
                    const sub = windowed[col - pad];
                    const number = offset + (col - pad) + 1;
                    return (
                      <td key={sub.id} className="px-1 py-1.5 text-center">
                        <StatusCell
                          status="passed"
                          tone={rankTone(sub.ranking)}
                          label={sub.ranking == null ? '?' : sub.ranking}
                          highlight={col === GRID_COLUMNS - 1}
                          title={`${team} — submission ${number} of ${subs.length} · ${
                            sub.ranking == null
                              ? 'no placement recorded'
                              : `placed #${sub.ranking} against the validation bots`
                          } · ${formatTimestamp(sub.timestamp)} · sim ${formatDuration(
                            sub.duration_ms
                          )} (click to view code)`}
                          onClick={() =>
                            setModalTarget({
                              teamName: team,
                              initialIndex: number - 1,
                            })
                          }
                        />
                      </td>
                    );
                  })}

                  <td className="px-3 py-1.5 text-center text-sm font-mono text-ui-dark">
                    {subs.length}
                  </td>
                  <td className="px-3 py-1.5 text-center">
                    <button
                      onClick={() =>
                        setModalTarget({
                          teamName: team,
                          initialIndex: subs.length - 1,
                        })
                      }
                      disabled={subs.length === 0}
                      title={`Step through all of ${team}'s submissions`}
                      className="px-3 py-1 rounded text-xs font-semibold border border-primary text-primary hover:bg-primary hover:text-white transition-colors disabled:opacity-40 disabled:border-ui-light disabled:text-ui-light disabled:hover:bg-transparent"
                    >
                      ALL
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {modalTarget && (
        <AgentCodeModal
          teamName={modalTarget.teamName}
          teamId={teamIds[modalTarget.teamName]}
          leagueId={league.id}
          submissions={modalSubmissions}
          initialIndex={modalTarget.initialIndex}
          onClose={() => setModalTarget(null)}
        />
      )}
    </div>
  );
}

export default SubmissionsTab;
