import React, { useMemo, useState } from 'react';
import CardRow from '../../../Shared/Cards/CardRow';
import PlayingCard from '../../../Shared/Cards/PlayingCard';
import TrickDisplay from '../../../Shared/Cards/TrickDisplay';
import { SUITS } from '../../../Shared/Cards/cardUtils';
import OhHellScoreBoard from './OhHellScoreBoard';

// step 0 = deal & bid, steps 1..cards = tricks
const OhHellFeedback = ({ feedback }) => {
    const [roundIndex, setRoundIndex] = useState(0);
    const [step, setStep] = useState(0);

    const players = feedback?.players || [];
    const rounds = feedback?.rounds || [];
    const round = rounds[roundIndex];

    const trick = step >= 1 ? round?.tricks[step - 1] : null;

    // Cards each player still holds entering the current step, and the card
    // they play this trick (kept in the row, highlighted).
    const { remaining, playedThisTrick } = useMemo(() => {
        if (!round) return { remaining: {}, playedThisTrick: {} };
        const rem = Object.fromEntries(players.map((p) => [p, [...round.dealt_hands[p]]]));
        round.tricks.slice(0, Math.max(0, step - 1)).forEach((t) => {
            t.plays.forEach(({ player, card }) => {
                rem[player] = rem[player].filter((c) => c !== card);
            });
        });
        const played = {};
        if (trick) trick.plays.forEach(({ player, card }) => { played[player] = card; });
        return { remaining: rem, playedThisTrick: played };
    }, [round, players, step, trick]);

    // Tricks each player has won so far this round, through the current trick
    const tricksWon = useMemo(() => {
        const won = Object.fromEntries(players.map((p) => [p, 0]));
        if (round) round.tricks.slice(0, step).forEach((t) => { won[t.winner] += 1; });
        return won;
    }, [round, players, step]);

    if (!round) {
        return <div className="text-ui-dark">No game data available</div>;
    }

    const scoresEnteringRound = roundIndex === 0
        ? Object.fromEntries(players.map((p) => [p, 0]))
        : rounds[roundIndex - 1].running_scores;

    const trumpSuit = SUITS[round.trump];

    const selectRound = (idx) => {
        setRoundIndex(idx);
        setStep(0);
    };

    const feedbackLines = trick
        ? trick.plays.filter((p) => p.feedback?.length).map((p) => ({ player: p.player, lines: p.feedback }))
        : [];

    // Did a player make their bid exactly? (only meaningful at end of round)
    const madeBid = (p) => tricksWon[p] === round.bids[p];

    return (
        <div className="bg-white p-6 rounded-lg shadow-lg space-y-6">
            {/* Game result banner */}
            <div className="text-center">
                <h2 className="text-xl font-bold text-ui-dark">
                    Oh Hell! — highest score wins
                </h2>
                <div className="text-success font-semibold text-lg">
                    Winner: {feedback.winner} 🏆
                </div>
            </div>

            {/* Round tabs */}
            <div className="flex flex-wrap gap-2 justify-center">
                {rounds.map((r, idx) => (
                    <button
                        key={r.round_number}
                        onClick={() => selectRound(idx)}
                        className={`px-3 py-2 rounded-lg font-medium transition-colors
                            ${idx === roundIndex ? 'bg-primary text-white' : 'bg-ui-lighter text-ui-dark hover:bg-ui-light'}`}
                    >
                        R{r.round_number}
                        <span className="text-xs opacity-80"> · {r.cards}🃏</span>
                        <span className={SUITS[r.trump].color === 'text-danger' ? 'text-danger' : ''}> {SUITS[r.trump].symbol}</span>
                    </button>
                ))}
            </div>

            {/* Round meta: trump + dealer */}
            <div className="flex items-center justify-center gap-4 text-sm text-ui">
                <span>
                    Trump:{' '}
                    <span className={`font-bold ${trumpSuit.color}`}>{trumpSuit.name} {trumpSuit.symbol}</span>
                </span>
                <span>·</span>
                <span>Dealer: <span className="font-semibold text-ui-dark">{round.dealer}</span></span>
                <span>·</span>
                <span>{round.cards} card{round.cards > 1 ? 's' : ''} each</span>
            </div>

            {/* Per-player status row: game score · bid vs tricks won */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {players.map((p) => (
                    <div key={p} className="bg-ui-lighter rounded-lg p-2 text-center">
                        <div className="text-sm font-semibold text-ui-dark truncate">{p}</div>
                        <div className="text-xs text-ui">
                            game {scoresEnteringRound[p]} · bid{' '}
                            <span className="font-semibold text-ui-dark">{round.bids[p]}</span>
                            {' '}won{' '}
                            <span className={`font-bold ${madeBid(p) ? 'text-success' : 'text-danger'}`}>
                                {tricksWon[p]}
                            </span>
                        </div>
                    </div>
                ))}
            </div>

            {/* Step content */}
            {step === 0 ? (
                <div className="space-y-4">
                    <h3 className="font-semibold text-ui-dark text-center">Deal &amp; bid</h3>
                    <div className="flex items-center justify-center gap-3">
                        <span className="text-sm text-ui">Trump card flipped:</span>
                        <PlayingCard card={round.trump_card} size="md" highlighted />
                    </div>
                    <div className="grid md:grid-cols-2 gap-3">
                        {players.map((p) => (
                            <div key={p} className="border border-ui-light rounded-lg p-3">
                                <div className="text-sm text-ui-dark mb-2 flex items-center justify-between">
                                    <span className="font-semibold">
                                        {p}{p === round.dealer && <span className="text-ui" title="dealer"> (D)</span>}
                                    </span>
                                    <span className="px-2 py-0.5 rounded-full bg-primary-light/20 text-primary-dark font-semibold text-xs">
                                        bids {round.bids[p]}
                                    </span>
                                </div>
                                <CardRow
                                    cards={round.dealt_hands[p]}
                                    size="sm"
                                    highlighted={round.dealt_hands[p].filter((c) => c.endsWith(round.trump))}
                                />
                            </div>
                        ))}
                    </div>
                    <div className="text-xs text-ui text-center">Highlighted cards are trumps</div>
                </div>
            ) : (
                <div className="space-y-4">
                    <div className="flex items-center justify-center gap-3 text-sm">
                        <span className="px-2 py-0.5 rounded-full bg-notice-yellowBg text-notice-orange font-semibold">
                            {trick.winner} takes the trick
                        </span>
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
                    {step === 0 ? 'Deal & Bid' : `Trick ${step} of ${round.tricks.length}`}
                </span>
                <button
                    onClick={() => setStep(step + 1)}
                    disabled={step === round.tricks.length}
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
                            cards={step === 0 ? round.dealt_hands[p] : remaining[p]}
                            size="sm"
                            highlighted={step === 0 ? [] : (playedThisTrick[p] ? [playedThisTrick[p]] : [])}
                        />
                    </div>
                ))}
                <div className="text-xs text-ui text-center">
                    {step === 0
                        ? 'Dealt hands'
                        : 'Cards held entering this trick — highlighted card is played'}
                </div>
            </div>

            {/* Full-game score sheet */}
            <OhHellScoreBoard
                players={players}
                rounds={rounds}
                finalScores={feedback.final_scores}
                winner={feedback.winner}
                selectedRound={roundIndex}
                onSelectRound={selectRound}
            />
        </div>
    );
};

export default OhHellFeedback;
