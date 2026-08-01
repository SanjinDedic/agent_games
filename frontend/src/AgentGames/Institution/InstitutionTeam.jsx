import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { toast } from 'react-toastify';
import { useSelector } from 'react-redux';
import useTeamManagementAPI from '../Shared/hooks/useTeamManagementAPI';
import useLeagueAPI from '../Shared/hooks/useLeagueAPI';
import { useTerms } from '../Shared/terminology';
import ResetLinkModal from '../Shared/ResetLinkModal';

/**
 * The institution-wide roster: every team regardless of classroom, with the
 * actions the per-classroom Students tab can't cover — managing unassigned or
 * cross-classroom teams, and creating a team without assigning it anywhere.
 * Unassigned teams sort first so the ones needing attention lead.
 */
function InstitutionTeam() {
  const T = useTerms();
  const leagues = useSelector((state) => state.leagues.list);
  const { getAllTeams, createTeam, deleteTeam, resetTeamPassword } = useTeamManagementAPI();
  const { fetchUserLeagues, assignTeamToLeague } = useLeagueAPI('institution');

  // null = still loading
  const [teams, setTeams] = useState(null);
  const [team, setTeam] = useState({ name: '', password: '', school_name: '' });
  const [showAddTeamForm, setShowAddTeamForm] = useState(false);
  // team id -> chosen league id string (uncommitted dropdown state)
  const [selections, setSelections] = useState({});
  const [actingTeamId, setActingTeamId] = useState(null);
  // { team_name, reset_token } while the share-this-reset-link modal is open
  const [resetTarget, setResetTarget] = useState(null);

  const load = useCallback(async () => {
    const result = await getAllTeams();
    setTeams(result.success ? result.data.teams : []);
  }, [getAllTeams]);

  useEffect(() => {
    load();
    fetchUserLeagues();
  }, [load, fetchUserLeagues]);

  const classrooms = useMemo(
    () => leagues.filter((l) => l.name !== 'unassigned'),
    [leagues]
  );
  // get-all-teams reports each team's league by name; the assign call needs ids
  const classroomIdByName = useMemo(
    () => new Map(classrooms.map((l) => [l.name, l.id])),
    [classrooms]
  );

  const sortedTeams = useMemo(() => {
    if (!teams) return [];
    const unassigned = (t) => (!t.league || t.league === 'unassigned' ? 0 : 1);
    return [...teams].sort(
      (a, b) => unassigned(a) - unassigned(b) || a.name.localeCompare(b.name)
    );
  }, [teams]);

  const handleChange = (e) => {
    setTeam((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleAddTeam = async () => {
    const result = await createTeam(team);
    if (result.success) {
      setTeam({ name: '', password: '', school_name: '' });
      setShowAddTeamForm(false);
      toast.success(`${T.Team} created successfully`);
      load();
    }
  };

  const handleAssign = async (row) => {
    const pending = selections[row.id];
    if (!pending) return;
    setActingTeamId(row.id);
    const result = await assignTeamToLeague(row.id, Number(pending));
    if (result.success) {
      const leagueName = classrooms.find((l) => l.id === Number(pending))?.name;
      toast.success(`'${row.name}' assigned to ${leagueName || `the ${T.league}`}`);
      setSelections((prev) => ({ ...prev, [row.id]: undefined }));
      await load();
    }
    setActingTeamId(null);
  };

  const handleDelete = async (row) => {
    if (!window.confirm(`Are you sure you want to delete ${T.team} "${row.name}"? All their submissions are deleted with them.`)) return;
    setActingTeamId(row.id);
    const result = await deleteTeam(row.id);
    if (result.success) {
      toast.success(result.data.message);
      await load();
    }
    setActingTeamId(null);
  };

  const handleResetPassword = async (row) => {
    const result = await resetTeamPassword(row.id);
    if (result.success) {
      setResetTarget(result.data);
    }
  };

  return (
    <div className="min-h-screen bg-ui-lighter pt-20 px-6 pb-8">
      <div className="max-w-[1800px] mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h1 className="text-2xl font-bold text-ui-dark mb-6">{`${T.Team} Management`}</h1>

          {teams === null ? (
            <div className="flex justify-center items-center h-32">
              <div className="text-lg text-ui-dark">{`Loading ${T.teams}...`}</div>
            </div>
          ) : (
            <div className="space-y-6">
              {teams.length === 0 ? (
                <p className="text-ui">{`No ${T.teams} yet — add one below.`}</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-ui-lighter">
                        <th className="px-4 py-3 text-left text-base font-semibold text-ui-dark">Name</th>
                        <th className="px-4 py-3 text-left text-base font-semibold text-ui-dark">School</th>
                        <th className="px-4 py-3 text-left text-base font-semibold text-ui-dark">{T.League}</th>
                        <th className="px-4 py-3 text-right text-base font-semibold text-ui-dark">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedTeams.map((row) => {
                        const currentId = classroomIdByName.get(row.league);
                        const value = selections[row.id] ?? String(currentId ?? '');
                        const canAssign =
                          selections[row.id] != null &&
                          selections[row.id] !== '' &&
                          selections[row.id] !== String(currentId ?? '');
                        return (
                          <tr key={row.id} className="border-b border-ui-light hover:bg-ui-lighter/50">
                            <td className="px-4 py-3 text-base font-medium text-ui-dark">{row.name}</td>
                            <td className="px-4 py-3 text-base text-ui">{row.school || '—'}</td>
                            <td className="px-4 py-3">
                              <select
                                value={value}
                                onChange={(e) =>
                                  setSelections((prev) => ({
                                    ...prev,
                                    [row.id]: e.target.value,
                                  }))
                                }
                                className="p-1.5 border border-ui-light rounded text-sm bg-white"
                                title={`Choose a ${T.league}`}
                              >
                                <option value="">unassigned</option>
                                {classrooms.map((classroom) => (
                                  <option key={classroom.id} value={classroom.id}>
                                    {classroom.name}
                                  </option>
                                ))}
                              </select>
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex gap-2 justify-end">
                                <button
                                  onClick={() => handleAssign(row)}
                                  disabled={!canAssign || actingTeamId === row.id}
                                  className="p-1.5 text-xs bg-success hover:bg-success-hover text-white rounded disabled:bg-ui-light disabled:cursor-not-allowed"
                                  title={`Move to the selected ${T.league}`}
                                >
                                  {actingTeamId === row.id ? 'Working…' : 'Assign'}
                                </button>
                                <button
                                  onClick={() => handleResetPassword(row)}
                                  disabled={actingTeamId === row.id}
                                  className="p-1.5 text-xs bg-primary hover:bg-primary-hover text-white rounded"
                                  title="Generate a password reset link"
                                >
                                  Reset
                                </button>
                                <button
                                  onClick={() => handleDelete(row)}
                                  disabled={actingTeamId === row.id}
                                  className="p-1.5 text-xs bg-danger hover:bg-danger-hover text-white rounded"
                                  title={`Delete ${T.team}`}
                                >
                                  X
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="space-y-4">
                <button
                  onClick={() => setShowAddTeamForm(!showAddTeamForm)}
                  className="w-full bg-success hover:bg-success-hover text-white py-3 rounded-lg text-lg font-medium transition-colors"
                >
                  {showAddTeamForm ? 'Cancel' : `Add a new ${T.team}`}
                </button>

                {showAddTeamForm && (
                  <div className="bg-ui-lighter p-6 rounded-lg space-y-4">
                    <h2 className="text-xl font-semibold text-ui-dark">{`Add ${T.Team}`}</h2>
                    <div className="space-y-4">
                      <input
                        type="text"
                        name="name"
                        value={team.name}
                        onChange={handleChange}
                        placeholder={`Enter ${T.team} name *`}
                        className="w-full p-3 border border-ui-light rounded-lg text-base focus:ring-2 focus:ring-primary focus:border-primary"
                      />
                      <input
                        type="text"
                        name="password"
                        value={team.password}
                        onChange={handleChange}
                        placeholder={`Enter ${T.team} password *`}
                        className="w-full p-3 border border-ui-light rounded-lg text-base focus:ring-2 focus:ring-primary focus:border-primary"
                      />
                      <input
                        type="text"
                        name="school_name"
                        value={team.school_name}
                        onChange={handleChange}
                        placeholder="Enter school name (optional)"
                        className="w-full p-3 border border-ui-light rounded-lg text-base focus:ring-2 focus:ring-primary focus:border-primary"
                      />
                      <button
                        onClick={handleAddTeam}
                        className="w-full bg-primary hover:bg-primary-hover text-white py-3 rounded-lg text-base font-medium transition-colors"
                      >
                        {`Add ${T.Team}`}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <ResetLinkModal
        teamName={resetTarget?.team_name}
        resetToken={resetTarget?.reset_token}
        onClose={() => setResetTarget(null)}
      />
    </div>
  );
}

export default InstitutionTeam;
