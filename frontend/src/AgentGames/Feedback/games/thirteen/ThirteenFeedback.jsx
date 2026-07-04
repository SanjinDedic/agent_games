import React, { useMemo, useState } from 'react';
import { useSelector } from 'react-redux';
import CardRow from '../../../Shared/Cards/CardRow';
import ComboPile from './ComboPile';

// step 0 = the deal; step k (1..N) = the state immediately after play k.
const ThirteenFeedback = ({ feedback }) => {
    const players = feedback?.players || [];
    const plays = feedback?.plays || [];
    const dealt = feedback?.dealt_hands || {};
    const placements = feedback?.placements || {};
    const userPlayer = useSelector((state) => state.teams.currentTeam);

    const [step, setStep] = useState(0);
    const total = plays.length;

    // Replay the log up to `step`: remaining hands, the live pile + owner, who
    // has passed on it, and the finish order revealed so far.
    const view = useMemo(() => {
        const remaining = Object.fromEntries(players.map((p) => [p, [...(dealt[p] || [])]]));
        let pile = [];
        let owner = null;
        let passed = new Set();
        const finished = [];
        for (let i = 0; i < step; i++) {
            const ev = plays[i];
            if (ev.action === 'play') {
                (ev.combo || []).forEach((c) => {
                    remaining[ev.seat] = remaining[ev.seat].filter((x) => x !== c);
                });
                pile = ev.combo;
                owner = ev.seat;
                passed = new Set();
                if (remaining[ev.seat].length === 0 && !finished.includes(ev.seat)) {
                    finished.push(ev.seat);
                }
            } else {
                passed = new Set(passed).add(ev.seat);
            }
            if (ev.cleared) {
                pile = [];
                owner = null;
                passed = new Set();
            }
        }
        return { remaining, pile, owner, passed, finished };
    }, [players, plays, dealt, step]);

    const acting = step >= 1 ? plays[step - 1] : null;

    if (!players.length) {
        return <div className="text-ui-dark">No game data available</div>;
    }

    const jump = (s) => setStep(Math.max(0, Math.min(total, s)));

    const stepLabel = () => {
        if (step === 0) return 'Deal — the lowest card leads';
        const verb =
            acting.action === 'pass'
                ? 'passes'
                : `plays ${acting.combo.join(' ')}`;
        return `Move ${step} / ${total} — ${acting.seat} ${verb}`;
    };

    return (
        <div className="bg-white p-6 rounded-lg shadow-lg space-y-6">
            {/* Result banner */}
            <div className="text-center">
                <h2 className="text-xl font-bold text-ui-dark">
                    Thirteen — first to shed all cards wins
                </h2>
                <div className="text-success font-semibold text-lg">
                    Winner: {feedback.winner} 🏆
                </div>
            </div>

            {/* Per-seat status: cards left · turn · placement */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {players.map((p) => {
                    const out = view.finished.includes(p);
                    const isTurn = acting && acting.seat === p;
                    const hasPassed = view.passed.has(p);
                    return (
                        <div
                            key={p}
                            className={`rounded-lg p-2 text-center border-2 transition-colors
                                ${isTurn ? 'border-primary bg-primary-light/10' : 'border-transparent bg-ui-lighter'}`}
                        >
                            <div className="text-sm font-semibold text-ui-dark truncate">
                                {p}
                                {p === userPlayer && <span className="text-primary"> (you)</span>}
                            </div>
                            <div className="text-xs">
                                {out ? (
                                    <span className="text-success font-bold">🏅 finished {placements[p]}</span>
                                ) : (
                                    <span className="text-ui">
                                        {view.remaining[p].length} cards
                                        {hasPassed && <span className="text-notice-orange"> · passed</span>}
                                    </span>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Central pile */}
            {step === 0 ? (
                <div className="text-center text-sm text-ui py-4 bg-ui-lighter rounded-lg">
                    13 cards each. The player holding the single lowest card opens.
                </div>
            ) : (
                <ComboPile combo={view.pile} owner={view.owner} userPlayer={userPlayer} />
            )}

            {/* Acting agent's own reasoning, if any */}
            {acting?.feedback?.length > 0 && (
                <div className="bg-ui-lighter rounded-lg p-3 text-sm space-y-1">
                    {acting.feedback.map((line, i) => (
                        <div key={i}>
                            <span className="font-semibold text-ui-dark">{acting.seat}:</span>{' '}
                            <span className="text-ui">{line}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* Step navigation */}
            <div className="flex flex-col items-center gap-2">
                <div className="flex justify-center items-center gap-4">
                    <button
                        onClick={() => jump(0)}
                        disabled={step === 0}
                        className="px-3 py-2 rounded-lg bg-ui-lighter hover:bg-ui-light disabled:opacity-50"
                    >
                        ⏮
                    </button>
                    <button
                        onClick={() => jump(step - 1)}
                        disabled={step === 0}
                        className="px-6 py-3 text-lg rounded-lg bg-ui-lighter hover:bg-ui-light disabled:opacity-50"
                    >
                        ←
                    </button>
                    <span className="text-sm text-ui-dark min-w-[16rem] text-center">{stepLabel()}</span>
                    <button
                        onClick={() => jump(step + 1)}
                        disabled={step === total}
                        className="px-6 py-3 text-lg rounded-lg bg-ui-lighter hover:bg-ui-light disabled:opacity-50"
                    >
                        →
                    </button>
                    <button
                        onClick={() => jump(total)}
                        disabled={step === total}
                        className="px-3 py-2 rounded-lg bg-ui-lighter hover:bg-ui-light disabled:opacity-50"
                    >
                        ⏭
                    </button>
                </div>
                <input
                    type="range"
                    min={0}
                    max={total}
                    value={step}
                    onChange={(e) => jump(Number(e.target.value))}
                    className="w-full max-w-xl"
                />
            </div>

            {/* Player hands (remaining) */}
            <div className="space-y-2">
                {players.map((p) => (
                    <div key={p} className="flex items-center gap-3">
                        <span className="w-32 shrink-0 text-sm font-semibold text-ui-dark text-right truncate">
                            {p}
                        </span>
                        {view.remaining[p].length ? (
                            <CardRow cards={view.remaining[p]} size="sm" />
                        ) : (
                            <span className="text-xs text-success font-semibold">— out —</span>
                        )}
                    </div>
                ))}
                <div className="text-xs text-ui text-center">
                    {step === 0 ? 'Dealt hands (sorted low → high)' : 'Cards still held'}
                </div>
            </div>

            {/* Final placement strip */}
            <div className="flex flex-wrap gap-2 justify-center pt-2 border-t border-ui-light">
                {feedback.finish_order?.map((p, i) => (
                    <span
                        key={p}
                        className={`px-3 py-1 rounded-full text-sm font-medium
                            ${i === 0 ? 'bg-success/15 text-success' : 'bg-ui-lighter text-ui-dark'}`}
                    >
                        {i + 1}. {p}
                    </span>
                ))}
            </div>
        </div>
    );
};

export default ThirteenFeedback;
