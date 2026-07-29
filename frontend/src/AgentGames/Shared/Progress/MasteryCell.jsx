import React from 'react';

/**
 * The two scales the concept views run on, and their colours.
 *
 * **Fluency** — how the finished work went — is the one with a verdict in it,
 * so it gets the heatmap: green → yellow → orange → red, deepening as the band
 * worsens, so the cells a teacher has to act on find their eye. The tones
 * differ in lightness as well as hue, so the grid still reads for someone who
 * cannot separate red from green.
 *
 * **Exposure** — how much of the work is finished — carries no verdict at all:
 * a student who has not got there yet is not failing, and colouring them red
 * for it is exactly how a teacher learns to distrust the page. So exposure is
 * one calm blue at every band and lets the bar's length do the talking.
 *
 * The bands themselves are defined in
 * backend/routes/institution/concept_mastery.py and travel with the matrix
 * payload — these are only their colours.
 */
export const BAND_TONES = {
  fluent: 'bg-success-light text-success hover:bg-success/25',
  showing_understanding: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200',
  progressing_slowly: 'bg-orange-200 text-orange-900 hover:bg-orange-300',
  needs_help: 'bg-red-300 text-red-900 hover:bg-red-400',
};

/** Solid fills for bars and dots, where a tint would disappear. */
export const BAND_BARS = {
  fluent: 'bg-success',
  showing_understanding: 'bg-yellow-400',
  progressing_slowly: 'bg-orange-400',
  needs_help: 'bg-danger',
};

/** Bordered chip version, for lists rather than grid squares. */
export const BAND_CHIPS = {
  fluent: 'bg-success-light border-success/30 text-success',
  showing_understanding: 'bg-yellow-100 border-yellow-300 text-yellow-800',
  progressing_slowly: 'bg-orange-100 border-orange-300 text-orange-800',
  needs_help: 'bg-danger-light border-danger/30 text-danger',
};

export const EXPOSURE_BAR = 'bg-primary-light';
export const EXPOSURE_CHIP = 'bg-primary/10 border-primary/30 text-primary-dark';

/**
 * The label and bar colour for a band key, read off the payload's own band
 * list so the words on screen are the words the backend scored with.
 */
export const fluencyTone = (scoring, key) => ({
  label: scoring.bands.find((band) => band.key === key)?.label || 'Not yet',
  bar: BAND_BARS[key] || 'bg-ui-light',
});

export const exposureTone = (scoring, key) => ({
  label:
    scoring.exposure_bands.find((band) => band.key === key)?.label ||
    'None yet',
  bar: EXPOSURE_BAR,
});

/**
 * One bar. The width is the percentage; the percentage itself is never
 * written down.
 *
 * This is the whole compromise the concept views run on. The arithmetic behind
 * these numbers is honest enough to rank students and to draw a length, and
 * nowhere near honest enough to tell a teacher a child is 68% of the way to
 * understanding dictionaries. A bar can be compared at a glance and cannot be
 * quoted in a report, which is exactly the amount of authority it has earned.
 */
export const Meter = ({ label, value, tone, muted }) => (
  <div className="min-w-0">
    <div className="flex items-baseline justify-between gap-2">
      <span className="text-xs uppercase tracking-wide text-ui">{label}</span>
      <span
        className={`text-xs font-medium truncate ${
          muted ? 'text-ui' : 'text-ui-dark'
        }`}
      >
        {value == null ? 'Not yet' : tone.label}
      </span>
    </div>
    <div className="mt-1 h-1.5 w-full rounded-full bg-ui-lighter overflow-hidden">
      <div
        className={`h-full rounded-full ${tone.bar}`}
        style={{ width: `${value ?? 0}%` }}
      />
    </div>
  </div>
);

/**
 * One square in the concept x student matrix, coloured by fluency band.
 *
 * `bandKey` is undefined for a concept the student has nothing judgeable on —
 * either they have not reached it, or they are still in the opening goes of
 * their first exercise. That renders as an inert dot, because neither is a
 * failure and neither must look like one. `showValue` swaps the swatch for its
 * band number when a teacher wants figures instead of colour.
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
