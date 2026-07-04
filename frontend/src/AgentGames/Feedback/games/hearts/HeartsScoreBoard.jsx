import React from 'react';

/**
 * Score sheet for a full Hearts game: one row per hand, one column per player,
 * plus running totals. Moon hands are flagged.
 */
const HeartsScoreBoard = ({ players, hands, finalScores, winner, selectedHand = null, onSelectHand = null }) => {
    return (
        <div className="w-full overflow-x-auto bg-white rounded-lg shadow border border-ui-light">
            <table className="w-full border-collapse text-sm">
                <thead>
                    <tr className="bg-league-blue text-white">
                        <th className="p-3 text-left font-semibold">Hand</th>
                        <th className="p-3 text-left font-semibold">Pass</th>
                        {players.map((p) => (
                            <th key={p} className={`p-3 text-right font-semibold ${p === winner ? 'underline decoration-2' : ''}`}>
                                {p}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {hands.map((hand, idx) => (
                        <tr
                            key={hand.hand_number}
                            onClick={onSelectHand ? () => onSelectHand(idx) : undefined}
                            className={`${idx % 2 === 0 ? 'bg-white' : 'bg-ui-lighter'}
                                ${selectedHand === idx ? 'outline outline-2 -outline-offset-2 outline-primary' : ''}
                                ${onSelectHand ? 'cursor-pointer hover:bg-primary-light/10' : ''}`}
                        >
                            <td className="p-3 font-medium border-b border-ui-light/30">
                                {hand.hand_number}
                                {hand.shot_the_moon && (
                                    <span className="ml-1" title={`${hand.shot_the_moon} shot the moon!`}>🌙</span>
                                )}
                            </td>
                            <td className="p-3 border-b border-ui-light/30 capitalize text-ui">{hand.pass_direction}</td>
                            {players.map((p) => (
                                <td key={p} className={`p-3 text-right border-b border-ui-light/30
                                    ${hand.shot_the_moon === p ? 'text-notice-orange font-bold' : hand.hand_scores[p] >= 13 ? 'text-danger font-semibold' : ''}`}>
                                    {hand.hand_scores[p]}
                                    {hand.shot_the_moon === p && ' 🌙'}
                                </td>
                            ))}
                        </tr>
                    ))}
                    <tr className="bg-ui-dark text-white font-bold">
                        <td className="p-3" colSpan={2}>Final (lowest wins)</td>
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

export default HeartsScoreBoard;
