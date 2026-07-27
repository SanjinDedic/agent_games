import React from 'react';

import { BAND_CHIPS } from './MasteryCell';

/**
 * "How is mastery calculated?" — the whole scoring model, in the teacher's
 * words, with the actual numbers in use.
 *
 * Everything rendered here comes from the `scoring` block of the concept
 * matrix payload, which the backend builds from the constants in
 * concept_mastery.py. Nothing is written out twice, so the explanation cannot
 * drift from the arithmetic: change a threshold and this page changes with it.
 */
function MasteryInfoModal({ scoring, onClose }) {
  if (!scoring) return null;

  const hintCap = Math.round(scoring.max_hint_effort / scoring.hint_effort_weight);
  const floorBand = scoring.bands.find(
    (band) => scoring.completion_floor >= band.minimum
  );

  return (
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-6"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start mb-4">
          <h3 className="text-xl font-bold text-ui-dark">
            How mastery is worked out
          </h3>
          <button
            onClick={onClose}
            className="text-ui hover:text-ui-dark text-2xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <p className="text-sm text-ui mb-5">
          Nothing here measures understanding directly — it measures what the
          work cost. An exercise that took one go means something different
          from the same exercise on the seventh go with every hint open, and
          that difference is all this page claims to show.
        </p>

        {/* The bands */}
        <h4 className="text-base font-semibold text-ui-dark mb-2">
          The four bands
        </h4>
        <div className="space-y-2 mb-5">
          {scoring.bands.map((band) => (
            <div key={band.key} className="flex items-start gap-3">
              <span
                className={`shrink-0 w-7 h-7 rounded-md border flex items-center justify-center text-sm font-bold ${
                  BAND_CHIPS[band.key]
                }`}
              >
                {band.band}
              </span>
              <div>
                <span className="text-sm font-semibold text-ui-dark">
                  {band.label}
                </span>{' '}
                <span className="text-xs font-mono text-ui">
                  {band.minimum}–{band.maximum}
                </span>
                <p className="text-sm text-ui">{band.meaning}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Step 1: one exercise */}
        <h4 className="text-base font-semibold text-ui-dark mb-2">
          Step 1 — what one exercise scores
        </h4>
        <p className="text-sm text-ui mb-2">
          Count the goes it took to pass. Each revealed hint adds{' '}
          {scoring.hint_effort_weight} of a go, and hints stop counting after{' '}
          {hintCap} of them — reading hints should cost a student something, but
          never as much as failing.
        </p>
        <table className="w-full text-sm mb-2">
          <thead>
            <tr className="text-left text-ui border-b border-ui-light">
              <th className="py-1 font-medium">Goes (including hints)</th>
              <th className="py-1 font-medium text-right">Scores</th>
            </tr>
          </thead>
          <tbody className="font-mono text-ui-dark">
            {scoring.effort_points.map((row, index) => {
              const previous =
                index === 0 ? 0 : scoring.effort_points[index - 1].max_effort;
              return (
                <tr key={row.max_effort} className="border-b border-ui-lighter">
                  <td className="py-1">
                    {index === 0
                      ? `first go, no hints`
                      : `over ${previous}, up to ${row.max_effort}`}
                  </td>
                  <td className="py-1 text-right">{row.points}</td>
                </tr>
              );
            })}
            <tr className="border-b border-ui-lighter">
              <td className="py-1">
                over{' '}
                {
                  scoring.effort_points[scoring.effort_points.length - 1]
                    .max_effort
                }
              </td>
              <td className="py-1 text-right">{scoring.effort_points_floor}</td>
            </tr>
            <tr>
              <td className="py-1">attempted, never passed</td>
              <td className="py-1 text-right">{scoring.not_passed_points}</td>
            </tr>
          </tbody>
        </table>

        {/* Step 2: one concept */}
        <h4 className="text-base font-semibold text-ui-dark mb-2 mt-5">
          Step 2 — from exercises to a concept
        </h4>
        <ul className="text-sm text-ui space-y-2 mb-5 list-disc pl-5">
          <li>
            The concept's score is the average over the exercises the student
            has <strong>actually attempted</strong>. Exercises they haven't
            reached yet are left out entirely — the cell stays blank rather than
            counting as a zero, because not having got there is not the same as
            not understanding it.
          </li>
          <li>
            <strong>
              Passing every exercise for a concept can never score below{' '}
              {scoring.completion_floor}
            </strong>
            , so it always lands in band{' '}
            {floorBand ? `${floorBand.band} or better` : 'two or better'} — no
            matter how many goes or hints it took. Finishing the work counts.
          </li>
        </ul>

        {/* How much to trust it */}
        <h4 className="text-base font-semibold text-ui-dark mb-2">
          How far to trust a cell
        </h4>
        <p className="text-sm text-ui">
          A concept practised on one exercise gives one data point. This page
          only states plainly that a student <em>is</em> struggling once its
          reading rests on {scoring.min_assessments} or more exercises;
          below that it says they <em>may be</em>, and concepts your course
          covers fewer than {scoring.min_assessments} times are flagged as
          lightly assessed. If a concept matters, it is worth practising at
          least {scoring.min_assessments} times.
        </p>
      </div>
    </div>
  );
}

export default MasteryInfoModal;
