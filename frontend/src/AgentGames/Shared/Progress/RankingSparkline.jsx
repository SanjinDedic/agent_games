import React from 'react';

/**
 * Dependency-free inline-SVG trend of a student's validation rankings.
 * `history` is [{ranking, timestamp}] oldest -> newest; rank 1 renders at the
 * top. Falls back to a dash when there is nothing ranked yet.
 */
const RankingSparkline = ({ history, width = 120, height = 28 }) => {
  if (!history || history.length === 0) {
    return <span className="text-base text-ui">—</span>;
  }

  const pad = 4;
  const rankings = history.map((entry) => entry.ranking);
  const worst = Math.max(...rankings, 2);
  const stepX =
    history.length > 1 ? (width - pad * 2) / (history.length - 1) : 0;
  // rank 1 -> top, worst rank -> bottom
  const yFor = (ranking) =>
    pad + ((ranking - 1) / (worst - 1)) * (height - pad * 2);
  const points = history.map((entry, i) => ({
    x: history.length > 1 ? pad + i * stepX : width / 2,
    y: yFor(entry.ranking),
    ...entry,
  }));

  const title = history
    .map((entry) => `#${entry.ranking}`)
    .join(' → ');

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="overflow-visible"
      role="img"
    >
      <title>{`Validation placements, oldest to newest: ${title}`}</title>
      {points.length > 1 && (
        <polyline
          points={points.map((p) => `${p.x},${p.y}`).join(' ')}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-primary/60"
        />
      )}
      {points.map((p, i) => (
        <circle
          key={i}
          cx={p.x}
          cy={p.y}
          r={p.ranking === 1 ? 3 : 2.25}
          className={p.ranking === 1 ? 'fill-amber-400' : 'fill-primary'}
        />
      ))}
    </svg>
  );
};

export default RankingSparkline;
