/**
 * The one green→red ramp the classroom views judge on.
 *
 * Every grid in the classroom section — concept fluency, exercise status,
 * validation placement — says some version of "this went well" through to
 * "this went badly", and before this file each said it in its own greens. A
 * teacher moving between the Concepts tab and Short Course Progress had to
 * relearn the colours on the way. So the ramp is defined once, here, and each
 * scale maps its own bands onto it.
 *
 * The eight stops step by hue at full saturation rather than by lightness:
 *
 *   1 emerald-500  2 green-400  3 lime-400   4 yellow-400
 *   5 amber-500    6 orange-500 7 orange-600 8 red-600
 *
 * which makes neighbours separable — stop 3 next to stop 4 is a real
 * difference at 32px — at the cost of weight: every cell in a grid now carries
 * a full-strength colour, so a class-sized grid reads loud, and it is the
 * spread of hue rather than any one cell that a teacher scans. Scales are
 * still free to skip stops, and the ones below do where the extra step would
 * be a distinction without a meaning.
 *
 * Each stop carries four renderings, because one colour cannot do all four
 * jobs:
 *   fill  — a whole grid square, with an ink dark enough to survive on it when
 *           the band-number toggle is on.
 *   solid — 12px legend dots and thin meter bars, where the same colour reads
 *           fine at a tenth the size.
 *   chip  — a bordered label in a list, rather than a square in a grid.
 *   ink   — text on the page's own white, for the glyph in a legend line that
 *           names what a coloured cell means. Two shades down from the stop,
 *           since lime and yellow at full strength vanish on white.
 *
 * Lightness peaks in the middle of this ramp instead of falling through it, so
 * the two ends separate for a teacher who cannot tell red from green but two
 * mid-ramp neighbours may not. That is what the band-number toggle above the
 * grid is for.
 *
 * This is NOT the brand palette. `success` and `danger` in tailwind.config.js
 * mean "this button saves" and "this button deletes"; they say nothing about a
 * student and must not be borrowed to. Reaching for `bg-success` to mean "this
 * child is doing fine" is how four different greens got into four adjacent
 * tabs in the first place.
 */
export const STOPS = {
  // emerald-500 #10b981
  1: {
    fill: 'bg-emerald-500 text-emerald-950 hover:bg-emerald-600',
    solid: 'bg-emerald-500',
    chip: 'bg-emerald-500 border-emerald-600 text-emerald-950',
    ink: 'text-emerald-600',
  },
  // green-400 #4ade80
  2: {
    fill: 'bg-green-400 text-green-950 hover:bg-green-500',
    solid: 'bg-green-400',
    chip: 'bg-green-400 border-green-500 text-green-950',
    ink: 'text-green-600',
  },
  // lime-400 #a3e635
  3: {
    fill: 'bg-lime-400 text-lime-950 hover:bg-lime-500',
    solid: 'bg-lime-400',
    chip: 'bg-lime-400 border-lime-500 text-lime-950',
    ink: 'text-lime-600',
  },
  // yellow-400 #facc15
  4: {
    fill: 'bg-yellow-400 text-yellow-950 hover:bg-yellow-500',
    solid: 'bg-yellow-400',
    chip: 'bg-yellow-400 border-yellow-500 text-yellow-950',
    ink: 'text-yellow-600',
  },
  // amber-500 #f59e0b
  5: {
    fill: 'bg-amber-500 text-amber-950 hover:bg-amber-600',
    solid: 'bg-amber-500',
    chip: 'bg-amber-500 border-amber-600 text-amber-950',
    ink: 'text-amber-600',
  },
  // orange-500 #f97316
  6: {
    fill: 'bg-orange-500 text-orange-950 hover:bg-orange-600',
    solid: 'bg-orange-500',
    chip: 'bg-orange-500 border-orange-600 text-orange-950',
    ink: 'text-orange-600',
  },
  // orange-600 #ea580c
  7: {
    fill: 'bg-orange-600 text-orange-950 hover:bg-orange-700',
    solid: 'bg-orange-600',
    chip: 'bg-orange-600 border-orange-700 text-orange-950',
    ink: 'text-orange-700',
  },
  // red-600 #dc2626
  8: {
    fill: 'bg-red-600 text-white hover:bg-red-700',
    solid: 'bg-red-600',
    chip: 'bg-red-600 border-red-700 text-white',
    ink: 'text-red-600',
  },
};

/** Neutral, for a cell with nothing to say rather than something bad to say. */
export const NEUTRAL = {
  fill: 'bg-ui-lighter text-ui border border-ui-light hover:bg-ui-light',
  solid: 'bg-ui-light',
  chip: 'border-ui-light text-ui',
  ink: 'text-ui',
};

const at = (stop, rendering) => (STOPS[stop] || NEUTRAL)[rendering];

/**
 * Validation placement, best first. Note where this stops: last place lands on
 * orange, never on red. Coming sixth against a row of validation bots is a
 * result, not a verdict on the student, and the bottom of the ramp is reserved
 * for the one scale that actually delivers one.
 */
export const PLACEMENT_STOPS = { 1: 1, 2: 2, 3: 3, 4: 4, 5: 5 };
export const PLACEMENT_TRAILING_STOP = 6;

/**
 * Exercise status. "Attempted" is not failure — it is a student mid-problem —
 * so it sits at yellow rather than anywhere in the oranges, and lets the
 * attempt count carry the signal.
 */
export const STATUS_STOPS = { passed: 2, attempted: 4 };

// One accessor per rendering the STOPS table defines, so the table and its
// readers stay in step even where a rendering currently has no caller.
export const stopFill = (stop) => at(stop, 'fill');
export const stopSolid = (stop) => at(stop, 'solid');
export const stopChip = (stop) => at(stop, 'chip');
export const stopInk = (stop) => at(stop, 'ink');

/** Build a {key: className} lookup from a {key: stop} mapping. */
export const tonesFor = (stops, rendering) =>
  Object.fromEntries(
    Object.entries(stops).map(([key, stop]) => [key, at(stop, rendering)])
  );
