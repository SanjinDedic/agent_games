import React from 'react';

/**
 * The mastery scale for the concept views. Four named bands, never a
 * percentage: no amount of attempt-counting justifies telling a teacher a
 * student is 68% of the way to understanding dictionaries. The bands are
 * defined in backend/routes/institution/concept_mastery.py and travel with the
 * matrix payload — these are only their colours.
 *
 * Green → yellow → orange → red, deepening as the band worsens so the two
 * bands a teacher has to act on carry the visual weight — the point of a
 * heatmap is that the cells needing attention find your eye, not that all
 * four tones are equally pretty. They differ in lightness as well as hue, so
 * the grid still reads for someone who can't separate red from green.
 */
export const BAND_TONES = {
  approaching_mastery: 'bg-success-light text-success hover:bg-success/25',
  showing_understanding: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200',
  progressing_slowly: 'bg-orange-200 text-orange-900 hover:bg-orange-300',
  needs_help: 'bg-red-300 text-red-900 hover:bg-red-400',
};

/** Solid fills for bars and dots, where a tint would disappear. */
export const BAND_BARS = {
  approaching_mastery: 'bg-success',
  showing_understanding: 'bg-yellow-400',
  progressing_slowly: 'bg-orange-400',
  needs_help: 'bg-danger',
};

/** Bordered chip version, for lists rather than grid squares. */
export const BAND_CHIPS = {
  approaching_mastery: 'bg-success-light border-success/30 text-success',
  showing_understanding: 'bg-yellow-100 border-yellow-300 text-yellow-800',
  progressing_slowly: 'bg-orange-100 border-orange-300 text-orange-800',
  needs_help: 'bg-danger-light border-danger/30 text-danger',
};

/** Bands the teacher is being asked to do something about. */
export const isAttentionBand = (band) => band >= 3;

/**
 * "is struggling" vs "may be struggling" — how firmly the page is allowed to
 * state a reading, given how many exercises it rests on. A concept practised
 * once is an anecdote, and saying otherwise is how a teacher learns to
 * distrust the whole tab.
 */
export const confidenceWording = (confidence) =>
  confidence === 'high' ? 'is' : 'may be';

/**
 * One square in the concept x student matrix.
 *
 * `bandKey` is the band's key, or undefined for a concept the student hasn't
 * reached — which renders as an inert dot, because not having got there yet is
 * not a failure and must not look like one. `showValue` swaps the swatch for
 * its band number when a teacher wants figures instead of colour.
 */
const MasteryCell = ({ band, bandKey, showValue, onClick, title }) => {
  if (!bandKey) {
    return (
      <span
        title={title}
        className="inline-flex w-8 h-8 items-center justify-center text-ui-light select-none"
      >
        ·
      </span>
    );
  }

  return (
    <button
      onClick={onClick}
      title={title}
      className={`inline-flex w-8 h-8 items-center justify-center rounded-md transition-colors ${
        showValue ? 'text-xs font-mono font-semibold' : 'text-sm font-bold'
      } ${BAND_TONES[bandKey]}`}
    >
      {showValue ? band : ''}
    </button>
  );
};

export default MasteryCell;
