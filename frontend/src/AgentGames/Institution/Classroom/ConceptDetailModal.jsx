import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

import { useLessonModal } from '../../Shared/Lesson/LessonModalContext';
import { useTerms } from '../../Shared/terminology';
import {
  BAND_BARS,
  BAND_CHIPS,
  confidenceWording,
  isAttentionBand,
} from '../../Shared/Progress/MasteryCell';

/**
 * Drill-down for one concept: who is struggling with it, which exercises
 * teach it, and the lesson to send them to.
 *
 * Everything here comes from the matrix payload the tab already holds — no
 * second request. Opened from a body cell it also gets `focusTeamId`, which
 * pins that student's figures at the top; opened from a concept row or the
 * reteach list it shows the class.
 *
 * This is the one place a raw score appears, and it appears labelled: the
 * bands are what the page means, the number is only how it sorts them.
 */
function ConceptDetailModal({
  concept,
  teams,
  cells,
  bands,
  minAssessments,
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

  // This concept's cells, weakest student first.
  const conceptCells = useMemo(() => {
    if (!concept) return [];
    return cells
      .filter((cell) => cell.concept_id === concept.id)
      .sort((a, b) => b.band - a.band || a.mastery - b.mastery);
  }, [cells, concept]);

  const focusCell = focusTeamId
    ? conceptCells.find((cell) => cell.team_id === focusTeamId)
    : null;

  if (!concept) return null;

  const bandLabel = (key) =>
    bands.find((band) => band.key === key)?.label || '';
  const needHelp = conceptCells.filter((cell) => isAttentionBand(cell.band));
  const notReached = teams.length - conceptCells.length;

  return (
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-6"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 flex flex-col"
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
            {`rests on very little. ${minAssessments} or more would make it `}
            {`something to act on.`}
          </p>
        )}

        {/* Class band */}
        <div className="mb-5">
          <div className="flex items-baseline justify-between mb-1">
            <span className="text-sm text-ui">The class</span>
            <span className="text-base font-semibold text-ui-dark">
              {concept.band_key ? bandLabel(concept.band_key) : 'Not reached'}
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-ui-lighter overflow-hidden">
            <div
              className={`h-full rounded-full ${
                BAND_BARS[concept.band_key] || 'bg-ui-light'
              }`}
              style={{ width: `${concept.class_mastery ?? 0}%` }}
            />
          </div>
          <p className="text-sm text-ui mt-2">
            {concept.reached} of {teams.length} {T.teams} have reached it
            {notReached > 0 && ` · ${notReached} not there yet`}
            {needHelp.length > 0 && (
              <span className="text-danger"> · {needHelp.length} need help</span>
            )}
          </p>
        </div>

        {/* The student this modal was opened from */}
        {focusCell && (
          <div className="mb-5 p-4 rounded-lg border border-primary/40 bg-primary/5">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <button
                onClick={() =>
                  navigate(`/Classroom/${leagueId}/student/${focusCell.team_id}`)
                }
                className="text-base font-semibold text-primary hover:text-primary-hover transition-colors"
              >
                {teamNames.get(focusCell.team_id)} →
              </button>
              <span
                className={`px-2 py-0.5 rounded border text-sm font-semibold ${
                  BAND_CHIPS[focusCell.band_key]
                }`}
              >
                {bandLabel(focusCell.band_key)}
              </span>
            </div>
            {isAttentionBand(focusCell.band) && (
              <p className="text-base text-ui-dark mt-1">
                {teamNames.get(focusCell.team_id)}{' '}
                {confidenceWording(focusCell.confidence)} struggling with{' '}
                {concept.name}.
              </p>
            )}
            <p className="text-sm text-ui mt-1">
              Passed {focusCell.exercises_passed} of{' '}
              {focusCell.exercises_touched} attempted exercises
              {focusCell.avg_attempts_to_pass &&
                ` · ${focusCell.avg_attempts_to_pass} tries to pass on average`}
              {` · ${focusCell.attempts} attempt${
                focusCell.attempts !== 1 ? 's' : ''
              } in total`}
              {focusCell.hints_used > 0 &&
                ` · ${focusCell.hints_used} hint${
                  focusCell.hints_used !== 1 ? 's' : ''
                } revealed`}
            </p>
            <p className="text-xs text-ui mt-1">
              score {focusCell.mastery}% — used for ordering only
            </p>
          </div>
        )}

        {/* Everyone who has reached it, weakest first */}
        {conceptCells.length > 0 && (
          <div className="mb-5">
            <h4 className="text-base font-semibold text-ui-dark mb-2">
              {T.Teams} — weakest first
            </h4>
            <div className="flex flex-wrap gap-2">
              {conceptCells.map((cell) => (
                <button
                  key={cell.team_id}
                  onClick={() =>
                    navigate(`/Classroom/${leagueId}/student/${cell.team_id}`)
                  }
                  className={`px-3 py-1 rounded-lg border text-sm transition-opacity hover:opacity-80 ${
                    BAND_CHIPS[cell.band_key]
                  }`}
                  title={
                    `${bandLabel(cell.band_key)} — passed ${
                      cell.exercises_passed
                    } of ${cell.exercises_touched} attempted` +
                    (cell.hints_used ? ` · ${cell.hints_used} hints` : '') +
                    ` (score ${cell.mastery}%)\nOpen their progress`
                  }
                >
                  {teamNames.get(cell.team_id)}{' '}
                  <span className="font-mono">{cell.band}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Where it is taught */}
        <div className="mb-5">
          <h4 className="text-base font-semibold text-ui-dark mb-2">
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
