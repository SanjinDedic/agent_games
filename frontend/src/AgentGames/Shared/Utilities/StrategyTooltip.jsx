import React, { useState } from 'react';

// Player name with a hover tooltip describing a validation player's strategy.
// Renders the tooltip with position:fixed so the results tables'
// overflow-x-auto wrappers can't clip it. Names without a strategy
// (user-submitted teams) render as plain text.
const StrategyTooltip = ({ name, strategy }) => {
    const [pos, setPos] = useState(null);

    if (!strategy) return <>{name}</>;

    const show = (e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        setPos({
            top: rect.bottom + 6,
            left: Math.min(rect.left, window.innerWidth - 300),
        });
    };

    return (
        <span
            className="cursor-help border-b border-dotted border-ui"
            onMouseEnter={show}
            onMouseLeave={() => setPos(null)}
        >
            {name}
            {pos && (
                <span
                    className="pointer-events-none fixed z-50 w-72 max-w-[80vw] rounded-lg bg-ui-dark p-3 text-sm font-normal normal-case text-white shadow-lg"
                    style={{ top: pos.top, left: pos.left }}
                >
                    {strategy}
                </span>
            )}
        </span>
    );
};

export default StrategyTooltip;
