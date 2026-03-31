import React from 'react';

const GOAL = 100;

const PLAYER_COLORS = [
    '#2563EB', '#10B981', '#8B5CF6', '#F59E0B',
    '#EF4444', '#06B6D4', '#EC4899', '#14B8A6',
];

const GreedyPigProgressBar = ({ roll, allPlayers }) => {
    const states = roll.all_players || {};

    let maxVal = GOAL;
    allPlayers.forEach(name => {
        const s = states[name];
        if (s) {
            const total = s.banked + s.unbanked;
            if (total > maxVal) maxVal = total;
        }
    });

    const goalPercent = (GOAL / maxVal) * 100;

    return (
        <div className="w-full mt-4 bg-ui-lighter rounded-lg p-4">
            <div className="relative">
                {allPlayers.map((name, idx) => {
                    const s = states[name] || { banked: 0, unbanked: 0 };
                    const total = s.banked + s.unbanked;
                    const bankedPercent = (s.banked / maxVal) * 100;
                    const unbankedPercent = (s.unbanked / maxVal) * 100;
                    const color = PLAYER_COLORS[idx % PLAYER_COLORS.length];

                    return (
                        <div key={name} className="flex items-center mb-2 last:mb-0 gap-3">
                            <div className="w-24 text-sm font-medium text-ui-dark text-right shrink-0 truncate">
                                {name}
                            </div>
                            <div className="flex-1 relative h-7 bg-white rounded border border-ui-light overflow-hidden">
                                {bankedPercent > 0 && (
                                    <div
                                        className="absolute top-0 left-0 h-full rounded-l transition-all duration-300"
                                        style={{ width: `${bankedPercent}%`, backgroundColor: color }}
                                    />
                                )}
                                {unbankedPercent > 0 && (
                                    <div
                                        className="absolute top-0 h-full transition-all duration-300 opacity-40"
                                        style={{
                                            left: `${bankedPercent}%`,
                                            width: `${unbankedPercent}%`,
                                            backgroundColor: color,
                                        }}
                                    />
                                )}
                                <div
                                    className="absolute top-0 h-full w-0.5 bg-notice-orange z-10"
                                    style={{ left: `${goalPercent}%` }}
                                />
                            </div>
                            <div className="w-12 text-sm font-bold text-ui-dark text-right shrink-0">
                                ${total}
                            </div>
                        </div>
                    );
                })}

                <div className="flex items-center justify-end gap-4 mt-3 text-xs text-ui">
                    <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded bg-league-blue" />
                        <span>Banked</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded bg-league-blue opacity-40" />
                        <span>Unbanked</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <div className="w-3 h-0.5 bg-notice-orange" />
                        <span>Goal (100)</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default GreedyPigProgressBar;
