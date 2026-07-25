import React from 'react';

/**
 * Validation placement scale for the submissions grid: 1 is a dark green that
 * fades through lighter greens, then yellow for the middle of the pack and
 * orange once the agent is being beaten by most of the validation bots.
 * `null`/unknown placements stay neutral rather than pretending to rank.
 */
const RANK_TONES = {
  1: 'bg-green-700 text-white hover:bg-green-800',
  2: 'bg-green-500 text-white hover:bg-green-600',
  3: 'bg-green-200 text-green-900 hover:bg-green-300',
  4: 'bg-yellow-200 text-yellow-900 hover:bg-yellow-300',
  5: 'bg-yellow-300 text-yellow-900 hover:bg-yellow-400',
};
const RANK_LOW = 'bg-orange-300 text-orange-900 hover:bg-orange-400';
const RANK_UNKNOWN = 'bg-ui-lighter text-ui border border-ui-light hover:bg-ui-light';

export const rankTone = (ranking) => {
  if (ranking == null) return RANK_UNKNOWN;
  return RANK_TONES[ranking] || RANK_LOW;
};

/**
 * One green/amber square in a progress matrix.
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
    tone ||
    (passed
      ? 'bg-green-100 text-green-700 hover:bg-green-200'
      : 'bg-amber-100 text-amber-700 hover:bg-amber-200');

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
