import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import { useSelector } from 'react-redux';
import { authFetch } from '../../utils/authFetch';
import { selectToken } from '../../slices/authSlice';
import { useTerms } from '../Shared/terminology';

// How many students the card shows before the "show all" toggle.
const COLLAPSED_COUNT = 2;

/**
 * Home-page card listing every team still in the institution's "unassigned"
 * holding pen, each with a classroom picker and an Assign button. Collapsed
 * to two rows by default so the card stays small next to the classroom cards.
 */
function UnassignedStudentsCard({ classrooms, onAssigned }) {
  const T = useTerms();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);

  // null = still loading
  const [students, setStudents] = useState(null);
  const [expanded, setExpanded] = useState(false);
  // team id -> chosen league id (uncommitted dropdown state)
  const [selections, setSelections] = useState({});
  const [assigningId, setAssigningId] = useState(null);

  const fetchUnassigned = useCallback(async () => {
    try {
      const response = await authFetch(`${apiUrl}/institution/get-all-teams`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      const data = await response.json();
      if (response.ok && Array.isArray(data.teams)) {
        setStudents(
          data.teams.filter((t) => !t.league || t.league === 'unassigned')
        );
      } else {
        setStudents([]);
        toast.error(data.detail || `Failed to load unassigned ${T.teams}`);
      }
    } catch (error) {
      console.error('Error fetching unassigned teams:', error);
      setStudents([]);
    }
  }, [apiUrl, accessToken]);

  useEffect(() => {
    fetchUnassigned();
  }, [fetchUnassigned]);

  const assign = async (student) => {
    const leagueId = selections[student.id] ?? classrooms[0]?.id;
    if (!leagueId) return;
    setAssigningId(student.id);
    try {
      const response = await authFetch(
        `${apiUrl}/institution/assign-team-to-league`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({
            team_id: student.id,
            league_id: Number(leagueId),
          }),
        }
      );
      const data = await response.json();
      if (response.ok) {
        const classroom = classrooms.find((c) => c.id === Number(leagueId));
        toast.success(
          `${student.name} assigned to ${classroom ? classroom.name : `the ${T.league}`}`
        );
        setStudents((prev) => prev.filter((s) => s.id !== student.id));
        if (onAssigned) onAssigned();
      } else {
        toast.error(data.detail || `Failed to assign ${T.team}`);
      }
    } catch (error) {
      console.error('Error assigning team:', error);
      toast.error(`Network error while assigning the ${T.team}`);
    } finally {
      setAssigningId(null);
    }
  };

  const visible =
    students && !expanded ? students.slice(0, COLLAPSED_COUNT) : students;
  const hiddenCount = students ? students.length - COLLAPSED_COUNT : 0;

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex justify-between items-baseline mb-2">
        <h2 className="text-xl font-bold text-ui-dark">
          {`Unassigned ${T.Teams}`}
        </h2>
        {students && students.length > 0 && (
          <span className="text-sm font-medium text-ui-dark bg-ui-lighter px-3 py-1 rounded-full whitespace-nowrap">
            {students.length}
          </span>
        )}
      </div>

      {students === null ? (
        <p className="text-sm text-ui">Loading…</p>
      ) : students.length === 0 ? (
        <p className="text-sm text-ui">
          {`Every ${T.team} is in a ${T.league} — nothing to assign.`}
        </p>
      ) : (
        <>
          <p className="text-sm text-ui mb-3">
            {`These ${T.teams} signed up but aren't in a ${T.league} yet — pick one and assign them.`}
          </p>
          <ul className="space-y-2">
            {visible.map((student) => (
              <li
                key={student.id}
                className="flex items-center gap-2 rounded-lg border border-ui-light p-2"
              >
                <span
                  className="flex-1 min-w-0 truncate font-medium text-ui-dark"
                  title={student.name}
                >
                  {student.name}
                </span>
                <select
                  value={selections[student.id] ?? classrooms[0]?.id ?? ''}
                  onChange={(e) =>
                    setSelections((prev) => ({
                      ...prev,
                      [student.id]: e.target.value,
                    }))
                  }
                  disabled={classrooms.length === 0}
                  className="max-w-[45%] p-1.5 border border-ui-light rounded text-sm bg-white"
                  title={`Choose a ${T.league}`}
                >
                  {classrooms.map((classroom) => (
                    <option key={classroom.id} value={classroom.id}>
                      {classroom.name}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => assign(student)}
                  disabled={assigningId === student.id || classrooms.length === 0}
                  className="px-3 py-1.5 bg-primary hover:bg-primary-hover text-white rounded text-sm font-medium transition-colors disabled:bg-ui-light disabled:cursor-not-allowed"
                >
                  {assigningId === student.id ? 'Assigning…' : 'Assign'}
                </button>
              </li>
            ))}
          </ul>
          {classrooms.length === 0 && (
            <p className="mt-2 text-xs text-ui">
              {`Create a ${T.league} first to assign these ${T.teams}.`}
            </p>
          )}
          {hiddenCount > 0 && (
            <button
              onClick={() => setExpanded((prev) => !prev)}
              className="mt-3 text-sm text-primary font-medium hover:underline"
            >
              {expanded
                ? 'Show fewer'
                : `Show all ${students.length} ${T.teams}`}
            </button>
          )}
        </>
      )}
    </div>
  );
}

export default UnassignedStudentsCard;
