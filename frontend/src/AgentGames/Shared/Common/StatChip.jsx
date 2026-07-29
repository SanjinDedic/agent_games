import React from 'react';

const TONES = {
  plain: 'bg-ui-lighter border-ui-light text-ui-dark',
  success: 'bg-success-light border-success/30 text-success',
  warning: 'bg-notice-orange/10 border-notice-orange/40 text-ui-dark',
  danger: 'bg-danger-light border-danger/30 text-danger',
};

/**
 * Small labelled figure used in the classroom overview and run summary rows.
 *
 * `tone` picks one of the brand tones above. `toneClass` overrides it outright,
 * for a chip that has to match a scale rather than the brand — the class
 * fluency chip wears its band's colour off the progress ramp so the headline
 * and the grid under it are saying the same thing in the same green.
 */
const StatChip = ({ label, value, tone = 'plain', toneClass, title }) => (
  <div
    className={`px-4 py-2 rounded-lg border ${toneClass || TONES[tone]}`}
    title={title}
  >
    {/* A ramp chip is a full-strength colour and sets its own text ink, which
        the usual grey label would fight — so borrow that ink and lighten it. */}
    <div
      className={`text-xs uppercase tracking-wide ${
        toneClass ? 'opacity-75' : 'text-ui'
      }`}
    >
      {label}
    </div>
    <div className="text-base font-semibold leading-tight">{value}</div>
  </div>
);

export default StatChip;
