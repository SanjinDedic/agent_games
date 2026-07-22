import React, { useEffect, useState } from 'react';

import useClassroomAPI from '../../Shared/hooks/useClassroomAPI';
import { useTerms } from '../../Shared/terminology';
import StatusCell from '../../Shared/Progress/StatusCell';
import ExerciseCodeModal from './ExerciseCodeModal';

/**
 * Student x exercise grid per tutorial: who passed what, who is stuck where
 * (attempt counts on amber cells), untouched as a dot. Clicking a touched
 * cell opens that student's submission history for the exercise.
 */
function TutorialMatrixTab({ league }) {
  const T = useTerms();
  const { getTutorialMatrix } = useClassroomAPI();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  // { teamId, teamName, exerciseId } while the code modal is open
  const [modalTarget, setModalTarget] = useState(null);

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      const result = await getTutorialMatrix(league.id);
      if (!active) return;
      if (result.success) {
        setData(result.data);
        setError('');
      } else {
        setError(result.error);
      }
      setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [getTutorialMatrix, league.id]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6 text-ui">
        {`Loading ${T.tutorial} progress…`}
      </div>
    );
  }
  if (error) {
    return <div className="bg-white rounded-lg shadow-lg p-6 text-danger">{error}</div>;
  }

  const teams = data?.teams || [];
  const tutorials = data?.tutorials || [];

  if (tutorials.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6 text-ui">
        {`No ${T.tutorials} are attached to this ${T.league} yet — attach them in the Settings tab.`}
      </div>
    );
  }
  if (teams.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6 text-ui">
        {`No ${T.teams} in this ${T.league} yet.`}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {tutorials.map((tutorial) => {
        const cells = new Map(
          tutorial.cells.map((cell) => [`${cell.team_id}:${cell.exercise_id}`, cell])
        );
        const passedPerExercise = (exerciseId) =>
          tutorial.cells.filter(
            (c) => c.exercise_id === exerciseId && c.status === 'passed'
          ).length;

        return (
          <div key={tutorial.id} className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 mb-1">
              <h2 className="text-xl font-semibold text-ui-dark">{tutorial.title}</h2>
              <span className="text-sm text-ui">
                {teams.length} {teams.length !== 1 ? T.teams : T.team}
              </span>
            </div>
            <p className="text-sm text-ui mb-4">
              <span className="text-green-700 font-bold">✓</span> passed ·{' '}
              <span className="text-amber-700 font-bold">n</span> attempts without a
              pass · <span className="font-bold">·</span> untouched — click a cell to
              read that {T.team}'s code.
            </p>
            <div className="overflow-x-auto">
              <table className="w-auto">
                <thead>
                  <tr className="bg-ui-lighter">
                    <th className="px-4 py-2 text-left text-sm font-semibold text-ui-dark sticky left-0 bg-ui-lighter z-10">
                      {T.Team}
                    </th>
                    {tutorial.exercises.map((exercise) => (
                      <th
                        key={exercise.id}
                        className="px-2 py-2 text-center text-sm font-semibold text-ui-dark w-10"
                        title={exercise.title}
                      >
                        {exercise.order_index + 1}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {teams.map((team) => (
                    <tr key={team.id} className="border-b border-ui-light hover:bg-ui-lighter/50">
                      <td className="px-4 py-1.5 text-base font-medium text-ui-dark whitespace-nowrap sticky left-0 bg-white z-10">
                        {team.name}
                      </td>
                      {tutorial.exercises.map((exercise) => {
                        const cell = cells.get(`${team.id}:${exercise.id}`);
                        return (
                          <td key={exercise.id} className="px-2 py-1.5 text-center">
                            <StatusCell
                              status={cell ? cell.status : 'untouched'}
                              attempts={cell?.attempts}
                              title={
                                cell
                                  ? `${team.name} — ${exercise.title}: ${
                                      cell.status === 'passed' ? 'passed' : 'not passed'
                                    } after ${cell.attempts} attempt${
                                      cell.attempts !== 1 ? 's' : ''
                                    } (click to view code)`
                                  : `${team.name} has not attempted ${exercise.title}`
                              }
                              onClick={() =>
                                setModalTarget({
                                  teamId: team.id,
                                  teamName: team.name,
                                  exerciseId: exercise.id,
                                })
                              }
                            />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                  {/* Per-exercise completion summary */}
                  <tr className="bg-ui-lighter/60">
                    <td className="px-4 py-2 text-sm font-semibold text-ui-dark sticky left-0 bg-ui-lighter z-10">
                      Passed
                    </td>
                    {tutorial.exercises.map((exercise) => (
                      <td
                        key={exercise.id}
                        className="px-2 py-2 text-center text-xs font-mono text-ui-dark"
                      >
                        {passedPerExercise(exercise.id)}/{teams.length}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        );
      })}

      {modalTarget && (
        <ExerciseCodeModal
          teamId={modalTarget.teamId}
          teamName={modalTarget.teamName}
          exerciseId={modalTarget.exerciseId}
          onClose={() => setModalTarget(null)}
        />
      )}
    </div>
  );
}

export default TutorialMatrixTab;
