import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { authFetch } from '../../utils/authFetch';
import { selectToken } from '../../slices/authSlice';
import { useTerms } from '../Shared/terminology';

const formatTimestamp = (ts) => {
  if (!ts) return '—';
  const d = new Date(ts);
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

/** Placement chip: gold / silver / bronze for validation ranks 1-3. */
const RANK_STYLES = {
  1: 'bg-amber-400 text-amber-950',
  2: 'bg-gray-300 text-gray-700',
  3: 'bg-amber-700 text-amber-50',
};

const PlacementBadge = ({ ranking }) => (
  <span
    className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-sm font-bold ${
      RANK_STYLES[ranking] || 'bg-ui-lighter text-ui border border-ui-light'
    }`}
  >
    {ranking}
  </span>
);

/** Completion bar: passed / total teams, colored by rate. */
const CompletionBar = ({ passed, total }) => {
  const pct = total > 0 ? Math.round((passed / total) * 100) : 0;
  const barColor =
    pct >= 75 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-400' : 'bg-red-400';
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden min-w-[80px]">
        <div
          className={`h-full ${barColor} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-sm font-mono text-ui-dark w-24 text-right">
        {passed}/{total} ({pct}%)
      </span>
    </div>
  );
};

function InstitutionProgress() {
  const T = useTerms();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);

  const [teams, setTeams] = useState([]);
  const [tutorials, setTutorials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchProgress = async () => {
      if (!accessToken) return;
      try {
        setLoading(true);
        setError('');
        const response = await authFetch(`${apiUrl}/institution/team-progress`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        const data = await response.json();
        if (response.ok) {
          setTeams(data.teams || []);
          setTutorials(data.tutorials || []);
        } else {
          setError(data.detail || `Failed to load ${T.team} progress`);
        }
      } catch (e) {
        console.error('Error fetching team progress:', e);
        setError(`Error fetching ${T.team} progress`);
      } finally {
        setLoading(false);
      }
    };
    fetchProgress();
  }, [apiUrl, accessToken]);

  return (
    <div className="min-h-screen bg-ui-lighter pt-20 px-6 pb-8">
      <div className="max-w-[1800px] mx-auto space-y-6">
        {loading ? (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex justify-center items-center h-32">
              <div className="text-lg text-ui-dark">{`Loading ${T.team} progress...`}</div>
            </div>
          </div>
        ) : error ? (
          <div className="bg-white rounded-lg shadow-lg p-6 text-danger">{error}</div>
        ) : (
          <>
            {/* Section 1: team submissions overview */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h1 className="text-2xl font-bold text-ui-dark mb-6">{`${T.Team} Progress`}</h1>
              {teams.length === 0 ? (
                <p className="text-ui">{`No ${T.teams} found for this account.`}</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-ui-lighter">
                        <th className="px-4 py-3 text-left text-base font-semibold text-ui-dark">{T.Team}</th>
                        <th className="px-4 py-3 text-left text-base font-semibold text-ui-dark">School</th>
                        <th className="px-4 py-3 text-left text-base font-semibold text-ui-dark">{T.League}</th>
                        <th className="px-4 py-3 text-right text-base font-semibold text-ui-dark">Attempts</th>
                        <th className="px-4 py-3 text-right text-base font-semibold text-ui-dark">Validated</th>
                        <th className="px-4 py-3 text-right text-base font-semibold text-ui-dark">Hints Used</th>
                        <th className="px-4 py-3 text-left text-base font-semibold text-ui-dark">Recent Placements</th>
                        <th className="px-4 py-3 text-center text-base font-semibold text-ui-dark">1st Place</th>
                        <th className="px-4 py-3 text-left text-base font-semibold text-ui-dark">Last Submission</th>
                      </tr>
                    </thead>
                    <tbody>
                      {teams.map((team) => (
                        <tr key={team.id} className="border-b border-ui-light hover:bg-ui-lighter/50">
                          <td className="px-4 py-3 text-base font-medium text-ui-dark">{team.name}</td>
                          <td className="px-4 py-3 text-base text-ui">{team.school}</td>
                          <td className="px-4 py-3 text-base text-ui">{team.league || '—'}</td>
                          <td className="px-4 py-3 text-base text-right font-mono text-ui-dark">{team.total_attempts}</td>
                          <td className="px-4 py-3 text-base text-right font-mono text-ui-dark">{team.validated_submissions}</td>
                          <td className="px-4 py-3 text-base text-right font-mono text-ui-dark">{team.hints_used}</td>
                          <td className="px-4 py-3">
                            {(team.recent_rankings || []).length === 0 ? (
                              <span className="text-base text-ui">—</span>
                            ) : (
                              <div
                                className="flex items-center gap-1.5"
                                title="Placements of the last 3 validated submissions, oldest to newest"
                              >
                                {team.recent_rankings.map((ranking, i) => (
                                  <PlacementBadge key={i} ranking={ranking} />
                                ))}
                              </div>
                            )}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {team.achieved_first && (
                              <span
                                className="text-success text-xl font-bold"
                                title={`This ${T.team} has reached 1st place`}
                              >
                                ✓
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-base text-ui">{formatTimestamp(team.latest_submission)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Section 2: per-tutorial exercise completion */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-bold text-ui-dark mb-2">Tutorial Progress</h2>
              <p className="text-ui mb-6">
                {`Completion rate per exercise across the ${T.teams} in each tutorial's ${T.leagues}.`}
              </p>
              {tutorials.length === 0 ? (
                <p className="text-ui">
                  {`No tutorials are attached to your ${T.leagues} yet. Attach tutorials from ${T.League} Management.`}
                </p>
              ) : (
                <div className="space-y-8">
                  {tutorials.map((tutorial) => (
                    <div key={tutorial.id}>
                      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 mb-3">
                        <h3 className="text-xl font-semibold text-ui-dark">{tutorial.title}</h3>
                        <span className="text-sm text-ui">
                          {tutorial.team_count} {tutorial.team_count !== 1 ? T.teams : T.team}
                          {tutorial.league_names.length > 0 &&
                            ` · ${T.leagues}: ${tutorial.league_names.join(', ')}`}
                        </span>
                      </div>
                      {tutorial.exercises.length === 0 ? (
                        <p className="text-ui text-sm">This tutorial has no exercises yet.</p>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="w-full">
                            <thead>
                              <tr className="bg-ui-lighter">
                                <th className="px-4 py-2 text-left text-sm font-semibold text-ui-dark w-12">#</th>
                                <th className="px-4 py-2 text-left text-sm font-semibold text-ui-dark">Exercise</th>
                                <th className="px-4 py-2 text-right text-sm font-semibold text-ui-dark w-28">Attempted</th>
                                <th className="px-4 py-2 text-right text-sm font-semibold text-ui-dark w-24">Passed</th>
                                <th className="px-4 py-2 text-left text-sm font-semibold text-ui-dark w-72">Completion</th>
                              </tr>
                            </thead>
                            <tbody>
                              {tutorial.exercises.map((exercise, index) => (
                                <tr key={exercise.id} className="border-b border-ui-light hover:bg-ui-lighter/50">
                                  <td className="px-4 py-2 text-sm font-mono text-ui">{index + 1}</td>
                                  <td className="px-4 py-2 text-base text-ui-dark">{exercise.title}</td>
                                  <td className="px-4 py-2 text-sm text-right font-mono text-ui-dark">
                                    {exercise.attempted_count}/{tutorial.team_count}
                                  </td>
                                  <td className="px-4 py-2 text-sm text-right font-mono text-ui-dark">
                                    {exercise.passed_count}/{tutorial.team_count}
                                  </td>
                                  <td className="px-4 py-2">
                                    <CompletionBar
                                      passed={exercise.passed_count}
                                      total={tutorial.team_count}
                                    />
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default InstitutionProgress;
