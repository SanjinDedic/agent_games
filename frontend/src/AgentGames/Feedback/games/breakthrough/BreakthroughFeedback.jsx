import React, { useState, useEffect, useMemo } from 'react';
import BreakthroughBoard from './BreakthroughBoard';

const SPEEDS = [
    { label: '1x', turnsPerSecond: 15 },
    { label: '2x', turnsPerSecond: 30 },
    { label: '4x', turnsPerSecond: 60 },
    { label: '8x', turnsPerSecond: 120 },
];

const RESULT_LABELS = {
    caught: 'Attacker caught!',
    breakthrough: 'Breakthrough!',
    timeout: 'Timeout — defender holds',
};

const BreakthroughFeedback = ({ feedback }) => {
    const [selectedPlayer, setSelectedPlayer] = useState('all');
    const [selectedMatch, setSelectedMatch] = useState(0);
    const [turnIndex, setTurnIndex] = useState(0);
    const [playing, setPlaying] = useState(false);
    const [speedIndex, setSpeedIndex] = useState(1);

    const players = useMemo(() => {
        const names = new Set();
        (feedback?.matches || []).forEach((match) => {
            names.add(match.attacker);
            names.add(match.defender);
        });
        return Array.from(names).sort();
    }, [feedback]);

    const filteredMatches = useMemo(() => {
        const matches = feedback?.matches || [];
        if (selectedPlayer === 'all') return matches;
        return matches.filter(
            (match) => match.attacker === selectedPlayer || match.defender === selectedPlayer
        );
    }, [feedback, selectedPlayer]);

    const match = filteredMatches[selectedMatch] || filteredMatches[0];
    const turns = match?.turns || [];
    const gridSize = match?.grid_size || 100;

    useEffect(() => {
        setSelectedMatch(0);
        setTurnIndex(0);
        setPlaying(false);
    }, [selectedPlayer, feedback]);

    useEffect(() => {
        if (!playing) return undefined;
        const interval = setInterval(() => {
            setTurnIndex((current) => {
                if (current >= turns.length) {
                    setPlaying(false);
                    return current;
                }
                return current + 1;
            });
        }, 1000 / SPEEDS[speedIndex].turnsPerSecond);
        return () => clearInterval(interval);
    }, [playing, speedIndex, turns.length]);

    const view = useMemo(() => {
        if (!match) return null;
        const attackerTrail = [match.start.a];
        const defenderTrail = [match.start.d];
        let attackerBoostsUsed = 0;
        let defenderBoostsUsed = 0;
        for (let i = 0; i < turnIndex && i < turns.length; i += 1) {
            attackerTrail.push(turns[i].a);
            defenderTrail.push(turns[i].d);
            attackerBoostsUsed += turns[i].ab;
            defenderBoostsUsed += turns[i].db;
        }
        return {
            attackerTrail,
            defenderTrail,
            attackerPos: attackerTrail[attackerTrail.length - 1],
            defenderPos: defenderTrail[defenderTrail.length - 1],
            attackerBoostsLeft: (match.boosts?.attacker ?? 5) - attackerBoostsUsed,
            defenderBoostsLeft: (match.boosts?.defender ?? 10) - defenderBoostsUsed,
        };
    }, [match, turns, turnIndex]);

    if (!feedback?.matches || feedback.matches.length === 0) {
        return <div className="text-ui-dark">No game data available</div>;
    }
    if (!match || !view) {
        return <div className="text-ui-dark">No matches found for the selected filters</div>;
    }

    const atEnd = turnIndex >= turns.length;
    const currentTurn = turnIndex > 0 ? turns[turnIndex - 1] : null;

    const handleMatchChange = (e) => {
        setSelectedMatch(parseInt(e.target.value, 10));
        setTurnIndex(0);
        setPlaying(false);
    };

    return (
        <div className="bg-white p-6 rounded-lg shadow-lg">
            <div className="mb-6 grid gap-4 sm:grid-cols-2">
                <div>
                    <label className="block text-ui-dark font-medium mb-2">Select Player</label>
                    <select
                        value={selectedPlayer}
                        onChange={(e) => setSelectedPlayer(e.target.value)}
                        className="w-full p-3 border border-ui-light rounded-lg bg-white text-ui-dark"
                    >
                        <option value="all">All Players</option>
                        {players.map((player) => (
                            <option key={player} value={player}>{player}</option>
                        ))}
                    </select>
                </div>
                <div>
                    <label className="block text-ui-dark font-medium mb-2">Select Match</label>
                    <select
                        value={selectedMatch}
                        onChange={handleMatchChange}
                        className="w-full p-3 border border-ui-light rounded-lg bg-white text-ui-dark"
                    >
                        {filteredMatches.map((m, index) => (
                            <option key={index} value={index}>
                                {m.attacker} (attack) vs {m.defender} (defend) — {RESULT_LABELS[m.result]}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="mb-4 flex flex-wrap items-center justify-center gap-x-8 gap-y-2 text-center">
                <div className="font-semibold">
                    <span className="text-danger">● {match.attacker}</span>
                    <span className="text-ui ml-2 text-sm">
                        attacker · boosts {view.attackerBoostsLeft}/{match.boosts?.attacker ?? 5}
                    </span>
                </div>
                <div className="font-semibold">
                    <span className="text-primary">● {match.defender}</span>
                    <span className="text-ui ml-2 text-sm">
                        defender · boosts {view.defenderBoostsLeft}/{match.boosts?.defender ?? 10}
                    </span>
                </div>
            </div>

            <div className="mb-4 text-center text-lg min-h-[1.75rem]">
                {atEnd ? (
                    <span className="text-success font-semibold">
                        {RESULT_LABELS[match.result]} (turn {match.end_turn})
                        {match.scores && (
                            <span className="text-ui-dark font-normal ml-3">
                                {match.attacker}: {match.scores[match.attacker]} · {match.defender}: {match.scores[match.defender]}
                            </span>
                        )}
                    </span>
                ) : (
                    <span className="text-ui">Turn {turnIndex} of {turns.length}</span>
                )}
            </div>

            <BreakthroughBoard
                gridSize={gridSize}
                attackerTrail={view.attackerTrail}
                defenderTrail={view.defenderTrail}
                attackerPos={view.attackerPos}
                defenderPos={view.defenderPos}
                caught={atEnd && match.result === 'caught'}
            />

            <div className="mt-6 flex items-center gap-4">
                <button
                    onClick={() => { setPlaying(false); setTurnIndex(0); }}
                    className="px-4 py-2 rounded-lg bg-ui-lighter hover:bg-ui-light"
                >
                    ⏮
                </button>
                <button
                    onClick={() => { setPlaying(false); setTurnIndex(Math.max(0, turnIndex - 1)); }}
                    disabled={turnIndex === 0}
                    className="px-4 py-2 rounded-lg bg-ui-lighter hover:bg-ui-light disabled:opacity-50"
                >
                    ←
                </button>
                <button
                    onClick={() => {
                        if (atEnd) setTurnIndex(0);
                        setPlaying(!playing);
                    }}
                    className="px-6 py-2 rounded-lg bg-primary text-white hover:bg-primary-hover font-semibold"
                >
                    {playing ? 'Pause' : 'Play'}
                </button>
                <button
                    onClick={() => { setPlaying(false); setTurnIndex(Math.min(turns.length, turnIndex + 1)); }}
                    disabled={atEnd}
                    className="px-4 py-2 rounded-lg bg-ui-lighter hover:bg-ui-light disabled:opacity-50"
                >
                    →
                </button>
                <select
                    value={speedIndex}
                    onChange={(e) => setSpeedIndex(parseInt(e.target.value, 10))}
                    className="p-2 border border-ui-light rounded-lg bg-white text-ui-dark"
                >
                    {SPEEDS.map((speed, index) => (
                        <option key={speed.label} value={index}>{speed.label}</option>
                    ))}
                </select>
            </div>

            <input
                type="range"
                min={0}
                max={turns.length}
                value={turnIndex}
                onChange={(e) => { setPlaying(false); setTurnIndex(parseInt(e.target.value, 10)); }}
                className="w-full mt-4"
            />

            {currentTurn && (currentTurn.af || currentTurn.df) && (
                <div className="mt-4 space-y-2 text-sm">
                    {currentTurn.af && (
                        <div className="p-3 bg-red-50 rounded-lg">
                            <span className="font-semibold text-danger">{match.attacker}: </span>
                            {currentTurn.af.join(' · ')}
                        </div>
                    )}
                    {currentTurn.df && (
                        <div className="p-3 bg-blue-50 rounded-lg">
                            <span className="font-semibold text-primary">{match.defender}: </span>
                            {currentTurn.df.join(' · ')}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default BreakthroughFeedback;
