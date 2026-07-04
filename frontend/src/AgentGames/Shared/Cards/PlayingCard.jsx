import React from 'react';
import { parseCard } from './cardUtils';

const SIZES = {
    sm: {
        box: 'w-8 h-11 rounded',
        corner: 'text-[0.6rem] leading-none px-0.5 pt-0.5',
        pip: 'text-sm',
        badge: 'w-4 h-4 text-[0.6rem] -top-1.5 -right-1.5',
    },
    md: {
        box: 'w-11 h-[3.85rem] rounded-md',
        corner: 'text-xs leading-none px-1 pt-1',
        pip: 'text-xl',
        badge: 'w-5 h-5 text-xs -top-2 -right-2',
    },
    lg: {
        box: 'w-14 h-20 rounded-lg',
        corner: 'text-sm leading-none px-1.5 pt-1.5',
        pip: 'text-3xl',
        badge: 'w-6 h-6 text-sm -top-2 -right-2',
    },
};

/**
 * Generic playing card. Reusable across card games.
 *
 * @param {string} card       Card code like "QS" or "10H" (ignored when faceDown)
 * @param {'sm'|'md'|'lg'} size
 * @param {boolean} faceDown  Render the card back
 * @param {boolean} highlighted  Emphasis ring (e.g. card just played / trick winner)
 * @param {boolean} dimmed    Fade out (e.g. already played)
 * @param {string|number} badge  Small corner badge (e.g. play order in a trick)
 */
const PlayingCard = ({ card, size = 'md', faceDown = false, highlighted = false, dimmed = false, badge = null }) => {
    const s = SIZES[size] || SIZES.md;

    const frame = `relative inline-flex flex-col select-none border shadow-sm ${s.box}
        ${highlighted ? 'ring-2 ring-primary border-primary shadow-md' : 'border-ui-light'}
        ${dimmed ? 'opacity-35' : ''}`;

    if (faceDown) {
        return (
            <div className={`${frame} bg-league-blue`}>
                <div className="absolute inset-1 rounded-sm border border-league-text/40 bg-[repeating-linear-gradient(45deg,transparent,transparent_3px,rgba(255,255,255,0.15)_3px,rgba(255,255,255,0.15)_6px)]" />
            </div>
        );
    }

    const { rank, symbol, color } = parseCard(card);

    return (
        <div className={`${frame} bg-white`}>
            <div className={`font-bold ${color} ${s.corner}`}>
                {rank}
                <span className="block">{symbol}</span>
            </div>
            <div className={`absolute inset-0 flex items-center justify-center ${color} ${s.pip} pt-2`}>
                {symbol}
            </div>
            {badge != null && (
                <span className={`absolute ${s.badge} flex items-center justify-center rounded-full bg-ui-dark text-white font-semibold z-10`}>
                    {badge}
                </span>
            )}
        </div>
    );
};

export default PlayingCard;
