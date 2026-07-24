import React from 'react';

const TONES = {
  plain: 'bg-ui-lighter border-ui-light text-ui-dark',
  success: 'bg-success-light border-success/30 text-success',
  warning: 'bg-notice-orange/10 border-notice-orange/40 text-ui-dark',
  danger: 'bg-danger-light border-danger/30 text-danger',
};

/** Small labelled figure used in the classroom overview and run summary rows. */
const StatChip = ({ label, value, tone = 'plain', title }) => (
  <div className={`px-4 py-2 rounded-lg border ${TONES[tone]}`} title={title}>
    <div className="text-xs uppercase tracking-wide text-ui">{label}</div>
    <div className="text-base font-semibold leading-tight">{value}</div>
  </div>
);

export default StatChip;
