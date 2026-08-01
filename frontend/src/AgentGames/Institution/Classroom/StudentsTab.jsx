import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import moment from 'moment-timezone';

import useClassroomAPI from '../../Shared/hooks/useClassroomAPI';
import useLeagueAPI from '../../Shared/hooks/useLeagueAPI';
import useTeamManagementAPI from '../../Shared/hooks/useTeamManagementAPI';
import { useTerms } from '../../Shared/terminology';
import ResetLinkModal from '../../Shared/ResetLinkModal';
import RankingSparkline from '../../Shared/Progress/RankingSparkline';

/**
 * Roster + progress for one classroom: per-student lifetime agent stats,
 * ranking trend, exercise completion and last-active, with the membership
 * actions (add / assign / reset password / unassign / delete) alongside.
 * Row click opens the student drill-down.
 */
function StudentsTab({ league }) {
  const T = useTerms();
  const navigate = useNavigate();
  const { getClassroomProgress } = useClassroomAPI();
  const { assignTeamToLeague, unassignTeam } = useLeagueAPI('institution');
  const { createTeam, deleteTeam, resetTeamPassword, getUnassignedTeams } = useTeamManagementAPI();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  // { team_name, reset_token } while the share-this-reset-link modal is open
  const [resetTarget, setResetTarget] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newStudent, setNewStudent] = useState({ name: '', password: '', school_name: '' });
  const [unassignedPool, setUnassignedPool] = useState([]);
  const [assignTeamId, setAssignTeamId] = useState('');

  const refresh = useCallback(async () => {
    const result = await getClassroomProgress(league.id);
    if (result.success) {
      setData(result.data);
      setError('');
    } else {
      setError(result.error);
    }
    setLoading(false);
  }, [getClassroomProgress, league.id]);

  const refreshUnassignedPool = useCallback(async () => {
    const result = await getUnassignedTeams();
    if (result.success) {
      setUnassignedPool(result.data.teams);
    }
  }, [getUnassignedTeams]);

  useEffect(() => {
    setLoading(true);
    refresh();
    refreshUnassignedPool();
  }, [refresh, refreshUnassignedPool]);

  const teams = useMemo(() => data?.teams || [], [data]);

  const handleAddStudent = async () => {
    const created = await createTeam(newStudent);
    if (!created.success) return;
    // New students land in 'unassigned'; move them straight into this classroom.
    const assigned = await assignTeamToLeague(created.data.team_id, league.id);
    if (assigned.success) {
      toast.success(`${T.Team} "${created.data.name}" added to ${league.name}`);
    }
    setNewStudent({ name: '', password: '', school_name: '' });
    setShowAddForm(false);
    refresh();
    refreshUnassignedPool();
  };

  const handleAssignExisting = async () => {
    if (!assignTeamId) {
      toast.error(`Please select a ${T.team} to assign`);
      return;
    }
    const chosen = unassignedPool.find((t) => String(t.id) === assignTeamId);
    const result = await assignTeamToLeague(assignTeamId, league.id);
    if (result.success) {
      toast.success(`'${chosen?.name || T.team}' assigned to ${league.name}`);
      setAssignTeamId('');
      refresh();
      refreshUnassignedPool();
    }
  };

  const handleUnassign = async (team) => {
    if (!window.confirm(`Move '${team.name}' to the 'unassigned' ${T.league}?`)) return;
    const result = await unassignTeam(team.id);
    if (result.success) {
      refresh();
      refreshUnassignedPool();
    }
  };

  const handleDelete = async (team) => {
    if (!window.confirm(`Are you sure you want to delete ${T.team} "${team.name}"? All their submissions are deleted with them.`)) return;
    const result = await deleteTeam(team.id);
    if (result.success) {
      toast.success(result.data.message);
      refresh();
    }
  };

  const handleResetPassword = async (team) => {
    const result = await resetTeamPassword(team.id);
    if (result.success) {
      setResetTarget(result.data);
    }
  };

  const lastActive = (ts) =>
    ts ? (
      <span title={new Date(ts).toLocaleString()}>{moment(ts).fromNow()}</span>
    ) : (
      '—'
    );

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6 text-ui">
        {`Loading ${T.teams}…`}
      </div>
    );
  }
  if (error) {
    return <div className="bg-white rounded-lg shadow-lg p-6 text-danger">{error}</div>;
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex flex-wrap justify-between items-center gap-2 mb-4">
          <h2 className="text-xl font-semibold text-ui-dark">
            {`${T.Teams} in ${league.name}`}
          </h2>
          <button
            onClick={() => setShowAddForm((v) => !v)}
            className="px-4 py-2 bg-success hover:bg-success-hover text-white text-sm rounded-lg transition-colors"
          >
            {showAddForm ? 'Cancel' : `Add ${T.team}`}
          </button>
        </div>

        {showAddForm && (
          <div className="bg-ui-lighter p-4 rounded-lg mb-6 space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <input
                type="text"
                value={newStudent.name}
                onChange={(e) => setNewStudent((p) => ({ ...p, name: e.target.value }))}
                placeholder={`${T.Team} name *`}
                className="p-2 border border-ui-light rounded-lg"
              />
              <input
                type="text"
                value={newStudent.password}
                onChange={(e) => setNewStudent((p) => ({ ...p, password: e.target.value }))}
                placeholder="Password *"
                className="p-2 border border-ui-light rounded-lg"
              />
              <input
                type="text"
                value={newStudent.school_name}
                onChange={(e) => setNewStudent((p) => ({ ...p, school_name: e.target.value }))}
                placeholder="School (optional)"
                className="p-2 border border-ui-light rounded-lg"
              />
            </div>
            <button
              onClick={handleAddStudent}
              className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg text-sm font-medium"
            >
              {`Add to ${league.name}`}
            </button>
            {unassignedPool.length > 0 && (
              <div className="flex items-center gap-2 pt-2 border-t border-ui-light">
                <span className="text-sm text-ui">Or assign an existing one:</span>
                <select
                  value={assignTeamId}
                  onChange={(e) => setAssignTeamId(e.target.value)}
                  className="p-2 border border-ui-light rounded-lg text-sm"
                >
                  <option value="">{`Select a ${T.team}`}</option>
                  {unassignedPool.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleAssignExisting}
                  className="px-3 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg text-sm"
                >
                  Assign
                </button>
              </div>
            )}
          </div>
        )}

        {teams.length === 0 ? (
          <p className="text-ui">
            {`No ${T.teams} in this ${T.league} yet — share the login link or add one above.`}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-ui-lighter">
                  <th className="px-4 py-3 text-left text-base font-semibold text-ui-dark">{T.Team}</th>
                  <th className="px-4 py-3 text-right text-base font-semibold text-ui-dark">Attempts</th>
                  <th className="px-4 py-3 text-right text-base font-semibold text-ui-dark">Validated</th>
                  <th className="px-4 py-3 text-right text-base font-semibold text-ui-dark">Hints</th>
                  <th className="px-4 py-3 text-left text-base font-semibold text-ui-dark" title="Validation placements over time, oldest to newest">Ranking Trend</th>
                  <th className="px-4 py-3 text-center text-base font-semibold text-ui-dark">Won vs bots</th>
                  <th className="px-4 py-3 text-right text-base font-semibold text-ui-dark" title={`Exercises passed / exercises in this ${T.league}'s ${T.tutorials}`}>Exercises</th>
                  <th className="px-4 py-3 text-left text-base font-semibold text-ui-dark" title="Most recent agent or exercise activity">Last Active</th>
                  <th className="px-4 py-3 text-right text-base font-semibold text-ui-dark">Actions</th>
                </tr>
              </thead>
              <tbody>
                {teams.map((team) => (
                  <tr
                    key={team.id}
                    className="border-b border-ui-light hover:bg-ui-lighter/50 cursor-pointer"
                    onClick={() => navigate(`/Classroom/${league.id}/student/${team.id}`)}
                    title={`Open ${team.name}'s submissions and progress`}
                  >
                    <td className="px-4 py-3 text-base font-medium text-primary hover:underline">
                      {team.name}
                    </td>
                    <td className="px-4 py-3 text-base text-right font-mono text-ui-dark">{team.total_attempts}</td>
                    <td className="px-4 py-3 text-base text-right font-mono text-ui-dark">{team.validated_submissions}</td>
                    <td className="px-4 py-3 text-base text-right font-mono text-ui-dark">{team.hints_used}</td>
                    <td className="px-4 py-3">
                      <RankingSparkline history={team.ranking_history} />
                    </td>
                    <td className="px-4 py-3 text-center">
                      {team.achieved_first && (
                        <span
                          className="text-success text-xl font-bold"
                          title={`This ${T.team} has won vs bots`}
                        >
                          ✓
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-base text-right font-mono text-ui-dark">
                      {team.exercises_total > 0
                        ? `${team.exercises_passed}/${team.exercises_total}`
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-base text-ui">{lastActive(team.last_active)}</td>
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <div className="flex gap-2 justify-end">
                        <button
                          onClick={() => handleResetPassword(team)}
                          className="p-1.5 text-xs bg-primary hover:bg-primary-hover text-white rounded"
                          title="Generate a password reset link"
                        >
                          Reset Password
                        </button>
                        <button
                          onClick={() => handleUnassign(team)}
                          className="p-1.5 text-xs bg-notice-orange hover:bg-notice-orange/90 text-white rounded"
                          title={`Move to the 'unassigned' ${T.league}`}
                        >
                          Unassign
                        </button>
                        <button
                          onClick={() => handleDelete(team)}
                          className="p-1.5 text-xs bg-danger hover:bg-danger-hover text-white rounded"
                          title={`Delete ${T.team}`}
                        >
                          X
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <ResetLinkModal
        teamName={resetTarget?.team_name}
        resetToken={resetTarget?.reset_token}
        onClose={() => setResetTarget(null)}
      />
    </div>
  );
}

export default StudentsTab;
