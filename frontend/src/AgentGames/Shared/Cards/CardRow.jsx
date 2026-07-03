import React from 'react';
import PlayingCard from './PlayingCard';

const OVERLAP = {
    sm: '-space-x-3',
    md: '-space-x-4',
    lg: '-space-x-5',
};

/**
 * A row of overlapping cards (a player's hand, a set of passed cards, ...).
 * Reusable across card games.
 *
 * @param {string[]} cards       Card codes, rendered in given order
 * @param {'sm'|'md'|'lg'} size
 * @param {boolean} overlap      Fan the cards with negative spacing
 * @param {Set|string[]} highlighted  Card codes to emphasise
 * @param {Set|string[]} dimmed  Card codes to fade out
 * @param {boolean} faceDown     Render all cards face down
 */
const CardRow = ({ cards = [], size = 'md', overlap = true, highlighted = [], dimmed = [], faceDown = false }) => {
    const hi = highlighted instanceof Set ? highlighted : new Set(highlighted);
    const dim = dimmed instanceof Set ? dimmed : new Set(dimmed);

    return (
        <div className={`flex flex-wrap items-center ${overlap ? OVERLAP[size] || OVERLAP.md : 'gap-1'}`}>
            {cards.map((card, i) => (
                <div key={`${card}-${i}`} className={hi.has(card) ? 'relative z-10 -translate-y-1' : ''}>
                    <PlayingCard
                        card={card}
                        size={size}
                        faceDown={faceDown}
                        highlighted={hi.has(card)}
                        dimmed={dim.has(card)}
                    />
                </div>
            ))}
        </div>
    );
};

export default CardRow;
