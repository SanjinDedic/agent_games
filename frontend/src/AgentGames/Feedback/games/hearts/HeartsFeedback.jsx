import React, { useMemo, useState } from 'react';
import CardRow from '../../../Shared/Cards/CardRow';
import TrickDisplay from '../../../Shared/Cards/TrickDisplay';
import HeartsScoreBoard from './HeartsScoreBoard';

const DIRECTION_ARROWS = { left: '←', right: '→', across: '↕', hold: '✋' };

// step 0 = deal & pass, steps 1..13 = tricks
const HeartsFeedback = ({ feedback }) => {
    const [handIndex, setHandIndex] = useState(0);
    const [step, setStep] = useState(0);

    const players = feedback?.players || [];
    const hands = feedback?.hands || [];
    const hand = hands[handIndex];

    const trick = step >= 1 ? hand?.tricks[step - 1] : null;

    // Cards each player still holds entering the current step, and the card
    // they play this trick (kept in the row, highlighted).
    const { remaining, playedThisTrick } = useMemo(() => {
        if (!hand) return { remaining: {}, playedThisTrick: {} };
        const rem = Object.fromEntries(players.map((p) => [p, [...hand.hands_after_pass[p]]]));
        hand.tricks.slice(0, Math.max(0, step - 1)).forEach((t) => {
            t.plays.forEach(({ player, card }) => {
                rem[player] = rem[player].filter((c) => c !== card);
            });
        });
        const played = {};
        if (trick) trick.plays.forEach(({ player, card }) => { played[player] = card; });
        return { remaining: rem, playedThisTrick: played };
    }, [hand, players, step, trick]);

    // Points taken so far in this hand, through the current trick
    const handPoints = useMemo(() => {
        const pts = Object.fromEntries(players.map((p) => [p, 0]));
        if (hand) hand.tricks.slice(0, step).forEach((t) => { pts[t.winner] += t.points; });
        return pts;
    }, [hand, players, step]);

    if (!hand) {
        return <div className="text-ui-dark">No game data available</div>;
    }

    const scoresEnteringHand = handIndex === 0
        ? Object.fromEntries(players.map((p) => [p, 0]))
        : hands[handIndex - 1].running_scores;

    const selectHand = (idx) => {
        setHandIndex(idx);
        setStep(0);
    };

    const feedbackLines = trick
        ? trick.plays.filter((p) => p.feedback?.length).map((p) => ({ player: p.player, lines: p.feedback }))
        : [];

    return (
        <div className="bg-white p-6 rounded-lg shadow-lg space-y-6">
            {/* Game result banner */}
            <div className="text-center">
                <h2 className="text-xl font-bold text-ui-dark">
                    Hearts — first to {feedback.target_score} loses
                </h2>
                <div className="text-success font-semibold text-lg">
                    Winner: {feedback.winner} 🏆
                </div>
            </div>

            {/* Hand tabs */}
            <div className="flex flex-wrap gap-2 justify-center">
                {hands.map((h, idx) => (
                    <button
                        key={h.hand_number}
                        onClick={() => selectHand(idx)}
                        className={`px-4 py-2 rounded-lg font-medium transition-colors
                            ${idx === handIndex ? 'bg-primary text-white' : 'bg-ui-lighter text-ui-dark hover:bg-ui-light'}`}
                    >
                        Hand {h.hand_number}{h.shot_the_moon ? ' 🌙' : ''}
                    </button>
                ))}
            </div>

            {/* Per-player status row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {players.map((p) => (
                    <div key={p} className="bg-ui-lighter rounded-lg p-2 text-center">
                        <div className="text-sm font-semibold text-ui-dark truncate">{p}</div>
                        <div className="text-xs text-ui">
                            game {scoresEnteringHand[p]} · hand <span className={handPoints[p] > 0 ? 'text-danger font-bold' : ''}>{handPoints[p]}</span>
                        </div>
                    </div>
                ))}
            </div>

            {/* Step content */}
            {step === 0 ? (
                <div className="space-y-4">
                    <h3 className="font-semibold text-ui-dark text-center">
                        Deal &amp; pass — <span className="capitalize">{hand.pass_direction}</span> {DIRECTION_ARROWS[hand.pass_direction]}
                    </h3>
                    {hand.passes ? (
                        <div className="grid md:grid-cols-2 gap-3">
                            {players.map((p) => (
                                <div key={p} className="border border-ui-light rounded-lg p-3">
                                    <div className="text-sm text-ui-dark mb-2">
                                        <span className="font-semibold">{p}</span> → {hand.passes[p].to}
                                    </div>
                                    <CardRow cards={hand.passes[p].cards} size="sm" overlap={false} />
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center text-ui">No passing this hand.</div>
                    )}
                </div>
            ) : (
                <div className="space-y-4">
                    <div className="flex items-center justify-center gap-3 text-sm">
                        {trick.hearts_broken && (
                            <span className="px-2 py-0.5 rounded-full bg-danger-light text-danger font-semibold">♥ broken</span>
                        )}
                        {trick.points > 0 && (
                            <span className="px-2 py-0.5 rounded-full bg-notice-yellowBg text-notice-orange font-semibold">
                                {trick.winner} takes {trick.points} pt{trick.points > 1 ? 's' : ''}
                            </span>
                        )}
                    </div>
                    <TrickDisplay
                        seats={players}
                        plays={trick.plays}
                        leader={trick.leader}
                        winner={trick.winner}
                    />
                    {feedbackLines.length > 0 && (
                        <div className="bg-ui-lighter rounded-lg p-3 text-sm space-y-1">
                            {feedbackLines.map(({ player, lines }) =>
                                lines.map((line, i) => (
                                    <div key={`${player}-${i}`}>
                                        <span className="font-semibold text-ui-dark">{player}:</span>{' '}
                                        <span className="text-ui">{line}</span>
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* Step navigation */}
            <div className="flex justify-center items-center gap-6">
                <button
                    onClick={() => setStep(step - 1)}
                    disabled={step === 0}
                    className="px-6 py-3 text-lg rounded-lg bg-ui-lighter hover:bg-ui-light disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    ←
                </button>
                <span className="text-lg text-ui-dark min-w-[10rem] text-center">
                    {step === 0 ? 'Deal & Pass' : `Trick ${step} of ${hand.tricks.length}`}
                </span>
                <button
                    onClick={() => setStep(step + 1)}
                    disabled={step === hand.tricks.length}
                    className="px-6 py-3 text-lg rounded-lg bg-ui-lighter hover:bg-ui-light disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    →
                </button>
            </div>

            {/* Player hands */}
            <div className="space-y-2">
                {players.map((p) => (
                    <div key={p} className="flex items-center gap-3">
                        <span className="w-28 shrink-0 text-sm font-semibold text-ui-dark text-right truncate">{p}</span>
                        <CardRow
                            cards={step === 0 ? hand.dealt_hands[p] : remaining[p]}
                            size="sm"
                            highlighted={step === 0
                                ? (hand.passes ? hand.passes[p].cards : [])
                                : (playedThisTrick[p] ? [playedThisTrick[p]] : [])}
                        />
                    </div>
                ))}
                <div className="text-xs text-ui text-center">
                    {step === 0
                        ? 'Dealt hands — highlighted cards are passed away'
                        : 'Cards held entering this trick — highlighted card is played'}
                </div>
            </div>

            {/* Full-game score sheet */}
            <HeartsScoreBoard
                players={players}
                hands={hands}
                finalScores={feedback.final_scores}
                winner={feedback.winner}
                selectedHand={handIndex}
                onSelectHand={selectHand}
            />
        </div>
    );
};

export default HeartsFeedback;
