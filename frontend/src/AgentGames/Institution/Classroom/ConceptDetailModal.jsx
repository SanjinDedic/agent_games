import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

import { useLessonModal } from '../../Shared/Lesson/LessonModalContext';
import { useTerms } from '../../Shared/terminology';
import {
  Meter,
  exposureTone,
  fluencyTone,
} from '../../Shared/Progress/MasteryCell';

/**
 * Drill-down for one concept: how the class is doing on it, how one student is
 * doing beside them, which exercises teach it, and the lesson to send them to.
 *
 * Everything here comes from the matrix payload the tab already holds — no
 * second request. Opened from a body cell it also gets `focusTeamId`, which
 * puts that student's bars beside the class's; opened from a concept row or
 * the reteach list it shows the class alone.
 *
 * Organised by scale rather than by subject — exposure, then fluency, each
 * with the student on the left and the class on the right. The other way round
 * makes a teacher hold one bar in their head while they look for its
 * counterpart, and the comparison is the entire reason both are here.
 */
function ConceptDetailModal({
  concept,
  teams,
  cells,
  scoring,
  leagueId,
  focusTeamId,
  onClose,
}) {
  const T = useTerms();
  const navigate = useNavigate();
  const { openLesson } = useLessonModal();

  const teamNames = useMemo(
    () => new Map(teams.map((team) => [team.id, team.name])),
    [teams]
  );

  // This concept's cells — the focused student's row, and the counts that say
  // how much of the class the class bars actually rest on.
  const conceptCells = useMemo(
    () =>
      concept ? cells.filter((cell) => cell.concept_id === concept.id) : [],
    [cells, concept]
  );

  const focusCell = focusTeamId
    ? conceptCells.find((cell) => cell.team_id === focusTeamId)
    : null;

  if (!concept) return null;

  const needHelp = conceptCells.filter((cell) => cell.needs_help);
  const notReached = teams.length - conceptCells.length;

  const studentName = focusCell ? teamNames.get(focusCell.team_id) : null;

  /** One scale: the student on the left, the class on the right. Falls back to
      the class alone when the modal was not opened from a student. */
  const scale = (title, tone, studentValue, studentKey, classValue, classKey) => (
    <div>
      <h4 className="text-sm font-semibold text-ui-dark mb-2">{title}</h4>
      <div className={focusCell ? 'grid grid-cols-2 gap-6' : ''}>
        {focusCell && (
          <Meter
            label={studentName}
            value={studentValue}
            tone={tone(scoring, studentKey)}
          />
        )}
        <Meter
          label="Class"
          value={classValue}
          tone={tone(scoring, classKey)}
          muted
        />
      </div>
    </div>
  );

  return (
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-6"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-xl font-bold text-ui-dark">{concept.name}</h3>
            <div className="flex flex-wrap items-center gap-2 mt-1">
              {concept.category && (
                <span className="px-2 py-0.5 rounded border border-ui-light bg-ui-lighter text-xs uppercase tracking-wide text-ui">
                  {concept.category.replace(/-/g, ' ')}
                </span>
              )}
              {concept.description && (
                <span className="text-sm text-ui">{concept.description}</span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-ui hover:text-ui-dark text-2xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* How well this concept is covered at all */}
        {concept.under_assessed && (
          <p className="mb-4 px-4 py-2 rounded-lg border border-notice-orange/40 bg-notice-orange/10 text-sm text-ui-dark">
            {`Only ${concept.exercises_total} exercise${
              concept.exercises_total !== 1 ? 's' : ''
            } in this ${T.league} practise this concept, so every reading below `}
            {`rests on very little. ${scoring.min_assessments} or more would `}
            {`make it something to act on.`}
          </p>
        )}

        {/* Who this reading is about, and how much of the class it rests on */}
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 mb-4">
          {focusCell ? (
            <button
              onClick={() =>
                navigate(`/Classroom/${leagueId}/student/${focusCell.team_id}`)
              }
              className="text-sm font-semibold text-ui-dark hover:text-primary transition-colors"
            >
              {studentName} →
            </button>
          ) : (
            <span className="text-sm font-semibold text-ui-dark">
              The class
            </span>
          )}
          <span className="text-xs text-ui">
            {concept.reached} of {teams.length} {T.teams} have reached it
            {notReached > 0 && ` · ${notReached} not there yet`}
            {needHelp.length > 0 && (
              <span className="text-danger"> · {needHelp.length} need help</span>
            )}
          </span>
        </div>

        {/* One scale at a time, the student against the class on each */}
        <div className="mb-5 space-y-4">
          {scale(
            'Exposure',
            exposureTone,
            focusCell?.exposure,
            focusCell?.exposure_band_key,
            concept.class_exposure,
            concept.exposure_band_key
          )}
          {scale(
            'Fluency',
            fluencyTone,
            focusCell?.fluency,
            focusCell?.band_key,
            concept.class_fluency,
            concept.band_key
          )}
          {focusCell && (
            <p className="text-xs text-ui">
              {`attempted ${focusCell.exercises_attempted}/${focusCell.exercises_total}`}
              {` · completed ${focusCell.exercises_passed}/${focusCell.exercises_total}`}
              {focusCell.avg_minutes_to_pass != null &&
                ` · ${focusCell.avg_minutes_to_pass} min to finish on average`}
              {focusCell.avg_attempts_to_pass &&
                ` · ${focusCell.avg_attempts_to_pass} goes to finish on average`}
              {focusCell.hints_used > 0 &&
                ` · ${focusCell.hints_used} hint${
                  focusCell.hints_used !== 1 ? 's' : ''
                } revealed`}
            </p>
          )}
        </div>

        {/* Where it is taught */}
        <div className="mb-5">
          <h4 className="text-sm font-semibold text-ui-dark mb-2">
            Exercises teaching this concept
          </h4>
          <ul className="space-y-1">
            {concept.exercises.map((exercise) => (
              <li key={exercise.id} className="text-sm text-ui">
                <span className="font-mono text-ui-dark">
                  {String(exercise.order_index + 1).padStart(2, '0')}
                </span>{' '}
                {exercise.title}
              </li>
            ))}
          </ul>
        </div>

        {/* The action: send them to the lesson */}
        {concept.lesson_slug ? (
          <button
            onClick={() => {
              onClose();
              openLesson(concept.lesson_slug);
            }}
            className="self-start px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg transition-colors"
          >
            Open the {concept.name} lesson
          </button>
        ) : (
          <p className="text-sm text-ui">
            No lesson is tagged with this concept yet.
          </p>
        )}
      </div>
    </div>
  );
}

export default ConceptDetailModal;
