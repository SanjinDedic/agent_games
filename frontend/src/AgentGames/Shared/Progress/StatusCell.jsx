import React from 'react';

import {
  NEUTRAL,
  PLACEMENT_STOPS,
  PLACEMENT_TRAILING_STOP,
  STATUS_STOPS,
  stopFill,
  stopInk,
} from './progressScale';

/** Ink for the ✓ / n glyphs in the legend line above a status grid. */
export const STATUS_INKS = {
  passed: stopInk(STATUS_STOPS.passed),
  attempted: stopInk(STATUS_STOPS.attempted),
};

/**
 * Validation placement scale for the submissions grid, walking straight down
 * the shared ramp one stop per place: green at the top, through lime and
 * yellow for the middle of the pack, to amber and then orange once the agent
 * is being beaten by most of the validation bots. `null`/unknown placements
 * stay neutral rather than pretending to rank.
 */
export const rankTone = (ranking) => {
  if (ranking == null) return NEUTRAL.fill;
  return stopFill(PLACEMENT_STOPS[ranking] || PLACEMENT_TRAILING_STOP);
};

/**
 * One green/yellow square in a progress matrix.
 * status: 'passed' | 'attempted' | 'untouched'; attempts shown for attempted
 * cells so "stuck after N tries" is visible at a glance.
 * `tone` swaps in another colour set (the submissions grid colours by
 * placement), `label` overrides the cell content, and `highlight` rings the
 * cell that matters most in its row.
 */
const StatusCell = ({ status, attempts, label, tone, highlight, onClick, title }) => {
  if (status === 'untouched') {
    return (
      <span
        title={title}
        className="inline-flex w-8 h-8 items-center justify-center text-ui-light select-none"
      >
        ·
      </span>
    );
  }

  const passed = status === 'passed';
  const colors =
    tone || stopFill(STATUS_STOPS[passed ? 'passed' : 'attempted']);

  return (
    <button
      onClick={onClick}
      title={title}
      className={`inline-flex w-8 h-8 items-center justify-center rounded-md font-bold transition-colors ${
        label != null ? 'text-xs font-mono' : 'text-sm'
      } ${colors} ${highlight ? 'ring-2 ring-primary ring-offset-1' : ''}`}
    >
      {label != null ? label : passed ? '✓' : attempts}
    </button>
  );
};

export default StatusCell;
