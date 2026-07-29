import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

import { useLessonModal } from '../../Shared/Lesson/LessonModalContext';
import { useTerms } from '../../Shared/terminology';
import {
  BAND_CHIPS,
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
 * pins that student's bars next to the class's; opened from a concept row or
 * the reteach list it shows the class alone.
 *
 * The class bars sit directly above the student's on purpose. "Slow on
 * dictionaries" means one thing when the rest of the class sailed through and
 * something completely different when nobody got it, and a teacher cannot tell
 * those apart from a single student's bar.
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

  // This concept's cells, weakest student first. Students with nothing
  // judgeable yet sort last: they are behind, not struggling.
  const conceptCells = useMemo(() => {
    if (!concept) return [];
    return cells
      .filter((cell) => cell.concept_id === concept.id)
      .sort((a, b) => {
        if (a.fluency == null && b.fluency == null) return 0;
        if (a.fluency == null) return 1;
        if (b.fluency == null) return -1;
        return a.fluency - b.fluency;
      });
  }, [cells, concept]);

  const focusCell = focusTeamId
    ? conceptCells.find((cell) => cell.team_id === focusTeamId)
    : null;

  if (!concept) return null;

  const bandLabel = (key) =>
    scoring.bands.find((band) => band.key === key)?.label || '';
  const needHelp = conceptCells.filter((cell) => cell.needs_help);
  const notReached = teams.length - conceptCells.length;

  /** The same two bars for the class and for one student, so they can be read
      as a pair rather than as two unrelated readings. */
  const pair = ({ exposure, fluency, exposureKey, fluencyKey, muted }) => (
    <div className="grid grid-cols-2 gap-4">
      <Meter
        label="Exposure"
        value={exposure}
        tone={exposureTone(scoring, exposureKey)}
        muted={muted}
      />
      <Meter
        label="Fluency"
        value={fluency}
        tone={fluencyTone(scoring, fluencyKey)}
        muted={muted}
      />
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

        {/* The class, then the student, on the same two scales */}
        <div className="mb-5 space-y-4">
          <div>
            <div className="flex items-baseline justify-between mb-2">
              <span className="text-sm font-semibold text-ui-dark">
                The class
              </span>
              <span className="text-xs text-ui">
                {concept.reached} of {teams.length} {T.teams} have reached it
                {notReached > 0 && ` · ${notReached} not there yet`}
                {needHelp.length > 0 && (
                  <span className="text-danger">
                    {' '}
                    · {needHelp.length} need help
                  </span>
                )}
              </span>
            </div>
            {pair({
              exposure: concept.class_exposure,
              fluency: concept.class_fluency,
              exposureKey: concept.exposure_band_key,
              fluencyKey: concept.band_key,
              muted: true,
            })}
          </div>

          {focusCell && (
            <div className="p-4 rounded-lg border border-primary/40 bg-primary/5">
              <div className="flex flex-wrap items-baseline justify-between gap-2 mb-2">
                <button
                  onClick={() =>
                    navigate(
                      `/Classroom/${leagueId}/student/${focusCell.team_id}`
                    )
                  }
                  className="text-sm font-semibold text-primary hover:text-primary-hover transition-colors"
                >
                  {teamNames.get(focusCell.team_id)} →
                </button>
                {focusCell.band_key && (
                  <span
                    className={`px-2 py-0.5 rounded border text-xs font-semibold ${
                      BAND_CHIPS[focusCell.band_key]
                    }`}
                  >
                    {bandLabel(focusCell.band_key)}
                  </span>
                )}
              </div>
              {pair({
                exposure: focusCell.exposure,
                fluency: focusCell.fluency,
                exposureKey: focusCell.exposure_band_key,
                fluencyKey: focusCell.band_key,
              })}
              <p className="text-xs text-ui mt-3">
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
            </div>
          )}
        </div>

        {/* Everyone who has reached it, weakest first */}
        {conceptCells.length > 0 && (
          <div className="mb-5">
            <h4 className="text-sm font-semibold text-ui-dark mb-2">
              {T.Teams} — weakest first
            </h4>
            <div className="flex flex-wrap gap-2">
              {conceptCells.map((cell) => (
                <button
                  key={cell.team_id}
                  onClick={() =>
                    navigate(`/Classroom/${leagueId}/student/${cell.team_id}`)
                  }
                  className={`px-3 py-1 rounded-lg border text-xs transition-opacity hover:opacity-80 ${
                    cell.band_key
                      ? BAND_CHIPS[cell.band_key]
                      : 'border-ui-light text-ui'
                  }`}
                  title={
                    (cell.band_key
                      ? `${bandLabel(cell.band_key)} — `
                      : 'Nothing judgeable yet — ') +
                    `attempted ${cell.exercises_attempted}/${cell.exercises_total}, ` +
                    `completed ${cell.exercises_passed}/${cell.exercises_total}` +
                    (cell.hints_used ? ` · ${cell.hints_used} hints` : '') +
                    `\nOpen their progress`
                  }
                >
                  {teamNames.get(cell.team_id)}{' '}
                  <span className="font-mono">{cell.band || '·'}</span>
                </button>
              ))}
            </div>
          </div>
        )}

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
