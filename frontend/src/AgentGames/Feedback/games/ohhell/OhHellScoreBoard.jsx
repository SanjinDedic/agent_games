import React from 'react';
import { SUITS } from '../../../Shared/Cards/cardUtils';

/**
 * Score sheet for a full Oh Hell game: one row per round, one column per player.
 * Each cell shows the round score, with the player's bid/tricks-won underneath —
 * green when they hit their bid exactly (and banked the bonus).
 */
const OhHellScoreBoard = ({ players, rounds, finalScores, winner, selectedRound = null, onSelectRound = null }) => {
    return (
        <div className="w-full overflow-x-auto bg-white rounded-lg shadow border border-ui-light">
            <table className="w-full border-collapse text-sm">
                <thead>
                    <tr className="bg-league-blue text-white">
                        <th className="p-3 text-left font-semibold">Round</th>
                        <th className="p-3 text-left font-semibold">Trump</th>
                        {players.map((p) => (
                            <th key={p} className={`p-3 text-right font-semibold ${p === winner ? 'underline decoration-2' : ''}`}>
                                {p}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {rounds.map((round, idx) => (
                        <tr
                            key={round.round_number}
                            onClick={onSelectRound ? () => onSelectRound(idx) : undefined}
                            className={`${idx % 2 === 0 ? 'bg-white' : 'bg-ui-lighter'}
                                ${selectedRound === idx ? 'outline outline-2 -outline-offset-2 outline-primary' : ''}
                                ${onSelectRound ? 'cursor-pointer hover:bg-primary-light/10' : ''}`}
                        >
                            <td className="p-3 font-medium border-b border-ui-light/30">
                                {round.round_number}
                                <span className="text-ui text-xs"> · {round.cards}🃏</span>
                            </td>
                            <td className={`p-3 border-b border-ui-light/30 font-semibold ${SUITS[round.trump].color}`}>
                                {SUITS[round.trump].symbol}
                            </td>
                            {players.map((p) => {
                                const made = round.tricks_won[p] === round.bids[p];
                                return (
                                    <td key={p} className="p-3 text-right border-b border-ui-light/30 align-top">
                                        <div className={`font-semibold ${made ? 'text-success' : 'text-ui-dark'}`}>
                                            +{round.round_scores[p]}
                                        </div>
                                        <div className="text-[0.7rem] text-ui">
                                            bid {round.bids[p]} · won {round.tricks_won[p]}
                                        </div>
                                    </td>
                                );
                            })}
                        </tr>
                    ))}
                    <tr className="bg-ui-dark text-white font-bold">
                        <td className="p-3" colSpan={2}>Final (highest wins)</td>
                        {players.map((p) => (
                            <td key={p} className="p-3 text-right">
                                {finalScores[p]}
                                {p === winner && ' 🏆'}
                            </td>
                        ))}
                    </tr>
                </tbody>
            </table>
        </div>
    );
};

export default OhHellScoreBoard;
