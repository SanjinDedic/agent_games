import React from 'react';

/** Placement chip: gold / silver / bronze for validation ranks 1-3. */
const RANK_STYLES = {
  1: 'bg-amber-400 text-amber-950',
  2: 'bg-gray-300 text-gray-700',
  3: 'bg-amber-700 text-amber-50',
};

const PlacementBadge = ({ ranking }) => (
  <span
    className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-sm font-bold ${
      RANK_STYLES[ranking] || 'bg-ui-lighter text-ui border border-ui-light'
    }`}
  >
    {ranking}
  </span>
);

export default PlacementBadge;
