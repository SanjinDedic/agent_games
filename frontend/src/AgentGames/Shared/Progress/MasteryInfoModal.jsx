import React from 'react';

import { BAND_CHIPS, EXPOSURE_CHIP } from './MasteryCell';

/**
 * "How is this worked out?" — the whole scoring model, in the teacher's words,
 * with the actual numbers in use.
 *
 * Everything rendered here comes from the `scoring` block of the concept
 * matrix payload, which the backend builds from the constants in
 * concept_mastery.py. Nothing is written out twice, so the explanation cannot
 * drift from the arithmetic: change a threshold and this page changes with it.
 */
function MasteryInfoModal({ scoring, onClose }) {
  if (!scoring) return null;

  const hintCap = Math.round(scoring.max_hint_penalty / scoring.hint_penalty);
  const covered = scoring.exposure_bands.find(
    (band) => band.band === scoring.covered_band
  );
  const attentionLabels = scoring.bands
    .filter((band) => scoring.attention_bands.includes(band.band))
    .map((band) => band.label.toLowerCase());

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
            How this is worked out
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
          work cost. Every concept gets two separate readings, because "hasn't
          done it" and "did it the hard way" are different problems and need
          different answers from you.
        </p>

        {/* The two scales */}
        <h4 className="text-base font-semibold text-ui-dark mb-1">
          Exposure — how much of it they have finished
        </h4>
        <p className="text-sm text-ui mb-2">
          The exercises they have completed, out of every exercise tagged with
          the concept. Nothing about exposure is a judgement: a student who has
          not got there yet is behind, not struggling.
        </p>
        <div className="flex flex-wrap gap-2 mb-5">
          {scoring.exposure_bands.map((band) => (
            <span
              key={band.key}
              className={`px-2 py-1 rounded border text-xs ${EXPOSURE_CHIP}`}
              title={band.meaning}
            >
              <span className="font-semibold">{band.label}</span>
            </span>
          ))}
        </div>

        <h4 className="text-base font-semibold text-ui-dark mb-1">
          Fluency — how the finished work went
        </h4>
        <p className="text-sm text-ui mb-2">
          The average score of the exercises they have finished, plus a zero for
          any they have really had a go at and never got through.
        </p>
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
                </span>
                <p className="text-sm text-ui">{band.meaning}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Step 1: one exercise */}
        <h4 className="text-base font-semibold text-ui-dark mb-2">
          What one exercise scores
        </h4>
        <p className="text-sm text-ui mb-2">
          An exercise finished within {scoring.free_minutes} minutes of the
          first submission is worth {scoring.full_marks}, however it was
          reached — a student who gets there that fast knew it, and charging
          them for the hints they read on the way only teaches them to avoid
          the hints. Past that, it starts at {scoring.full_marks} and pays:
        </p>
        <table className="w-full text-sm mb-2">
          <tbody className="text-ui-dark">
            <tr className="border-b border-ui-lighter">
              <td className="py-1">
                every further {scoring.minutes_per_step} minutes
              </td>
              <td className="py-1 text-right font-mono">
                −{scoring.time_penalty_step}
              </td>
              <td className="py-1 text-right text-ui text-xs whitespace-nowrap">
                stops at −{scoring.max_time_penalty}
              </td>
            </tr>
            <tr className="border-b border-ui-lighter">
              <td className="py-1">each hint revealed</td>
              <td className="py-1 text-right font-mono">
                −{scoring.hint_penalty}
              </td>
              <td className="py-1 text-right text-ui text-xs whitespace-nowrap">
                stops after {hintCap}
              </td>
            </tr>
            <tr className="border-b border-ui-lighter">
              <td className="py-1">
                more than {scoring.many_attempts} goes to get through it
              </td>
              <td className="py-1 text-right font-mono">
                −{scoring.many_attempts_penalty}
              </td>
              <td className="py-1 text-right text-ui text-xs whitespace-nowrap">
                once, not per go
              </td>
            </tr>
            <tr>
              <td className="py-1">
                had real goes at it and never got through
              </td>
              <td className="py-1 text-right font-mono">
                {scoring.not_passed_points}
              </td>
              <td className="py-1 text-right text-ui text-xs whitespace-nowrap">
                after {scoring.attempts_before_counted} goes
              </td>
            </tr>
          </tbody>
        </table>
        <p className="text-sm text-ui mb-5">
          So a finished exercise can never score below{' '}
          <strong>{scoring.completed_floor}</strong>, however long it took.
          Finishing counts. The clock runs from their first submission, not from
          opening the exercise — reading and thinking before the first go is
          free.
        </p>

        {/* The rule */}
        <h4 className="text-base font-semibold text-ui-dark mb-2">
          When someone is flagged
        </h4>
        <p className="text-sm text-ui mb-5">
          Only when <strong>both</strong> are true: exposure is "
          {covered ? covered.label.toLowerCase() : 'most or all'}", so there is
          nothing left for them to simply get on with, and fluency is{' '}
          {attentionLabels.join(' or ')}. Because a finished exercise cannot
          score below {scoring.completed_floor}, falling under that line always
          means work they had real goes at and never got through. A student
          part-way into a concept is never flagged — there is nothing to
          conclude yet, and flagging them is how a teacher learns to ignore the
          page. The same test applied to the class as a whole is what puts a
          concept on the reteach list.
        </p>

        <h4 className="text-base font-semibold text-ui-dark mb-2">
          How far to trust it
        </h4>
        <p className="text-sm text-ui">
          A concept practised on one exercise gives one data point, and its
          exposure can only ever be nothing or everything. Concepts your course
          covers fewer than {scoring.min_assessments} times are flagged as
          lightly assessed throughout. If a concept matters, it is worth
          practising at least {scoring.min_assessments} times.
        </p>
      </div>
    </div>
  );
}

export default MasteryInfoModal;
