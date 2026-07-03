import React from 'react';
import PlayingCard from './PlayingCard';

// Seat placement for up to 4 players around a table: index 0 = bottom (south),
// then clockwise. Grid is 3x3; centre is decoration only.
const SEAT_CLASSES = [
    'col-start-2 row-start-3', // south
    'col-start-1 row-start-2', // west
    'col-start-2 row-start-1', // north
    'col-start-3 row-start-2', // east
];

/**
 * The cards played to a single trick, laid out around a table.
 * Reusable across trick-taking card games.
 *
 * @param {string[]} seats   Player names in seat order (index 0 rendered at the bottom)
 * @param {Array}    plays   [{ player, card }] in the order the cards were played
 * @param {string}   leader  Player who led the trick
 * @param {string}   winner  Player who took the trick (highlighted)
 * @param {string}   userPlayer  Optional player name to tint as "you"
 */
const TrickDisplay = ({ seats = [], plays = [], leader = null, winner = null, userPlayer = null }) => {
    const playByPlayer = {};
    plays.forEach((p, i) => {
        playByPlayer[p.player] = { ...p, order: i + 1 };
    });

    return (
        <div className="grid grid-cols-3 grid-rows-3 gap-1 place-items-center bg-success/10 border border-success/30 rounded-2xl px-4 py-3 min-h-[16rem]">
            {seats.map((player, i) => {
                const play = playByPlayer[player];
                const isWinner = winner === player;
                return (
                    <div key={player} className={`${SEAT_CLASSES[i % 4]} flex flex-col items-center gap-1`}>
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full whitespace-nowrap
                            ${isWinner ? 'bg-success text-white' : userPlayer === player ? 'bg-primary text-white' : 'bg-ui-lighter text-ui-dark'}`}>
                            {player}
                            {leader === player && <span title="led the trick"> •lead</span>}
                        </span>
                        {play ? (
                            <PlayingCard card={play.card} size="md" badge={play.order} highlighted={isWinner} />
                        ) : (
                            <div className="w-11 h-[3.85rem] rounded-md border-2 border-dashed border-ui-light/70" />
                        )}
                    </div>
                );
            })}
        </div>
    );
};

export default TrickDisplay;
