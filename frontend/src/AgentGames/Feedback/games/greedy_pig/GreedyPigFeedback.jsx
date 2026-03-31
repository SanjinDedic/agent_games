import React, { useState, useEffect } from 'react';
import GreedyPigRoundView from './GreedyPigRoundView';
import GreedyPigProgressBar from './GreedyPigProgressBar';
import GreedyPigPlayerFeedback from './GreedyPigPlayerFeedback';

const GreedyPigFeedback = ({ feedback }) => {
    const [currentRoundIndex, setCurrentRoundIndex] = useState(0);
    const [currentRollIndex, setCurrentRollIndex] = useState(0);
    const [players, setPlayers] = useState([]);

    useEffect(() => {
        if (feedback?.rounds?.length > 0) {
            const uniquePlayers = new Set();
            feedback.rounds.forEach(round => {
                round.rolls.forEach(roll => {
                    roll.players.forEach(p => uniquePlayers.add(p.name));
                });
            });
            setPlayers(Array.from(uniquePlayers).sort());
        }
    }, [feedback]);

    if (!feedback?.rounds || feedback.rounds.length === 0) {
        return <div className="text-ui-dark">No game data available</div>;
    }

    const rounds = feedback.rounds;
    const currentRound = rounds[currentRoundIndex];
    const rolls = currentRound?.rolls || [];
    const currentRoll = rolls[currentRollIndex];

    const totalRolls = rounds.reduce((sum, r) => sum + r.rolls.length, 0);

    let globalRollIndex = 0;
    for (let i = 0; i < currentRoundIndex; i++) {
        globalRollIndex += rounds[i].rolls.length;
    }
    globalRollIndex += currentRollIndex;

    const handleNext = () => {
        if (currentRollIndex < rolls.length - 1) {
            setCurrentRollIndex(currentRollIndex + 1);
        } else if (currentRoundIndex < rounds.length - 1) {
            setCurrentRoundIndex(currentRoundIndex + 1);
            setCurrentRollIndex(0);
        }
    };

    const handlePrevious = () => {
        if (currentRollIndex > 0) {
            setCurrentRollIndex(currentRollIndex - 1);
        } else if (currentRoundIndex > 0) {
            const prevRound = rounds[currentRoundIndex - 1];
            setCurrentRoundIndex(currentRoundIndex - 1);
            setCurrentRollIndex(prevRound.rolls.length - 1);
        }
    };

    const isFirst = currentRoundIndex === 0 && currentRollIndex === 0;
    const isLast = currentRoundIndex === rounds.length - 1 && currentRollIndex === rolls.length - 1;

    const currentPlayerFeedback = currentRoll?.players
        ?.filter(p => p.player_feedback && p.player_feedback.length > 0)
        || [];

    return (
        <div className="bg-white p-6 rounded-lg shadow-lg">
            <div className="mb-4 text-center">
                <h2 className="text-xl font-bold text-ui-dark">
                    Round {currentRound.round_no}
                </h2>
                <div className="text-lg text-ui">
                    Roll {currentRoll?.roll_no}
                    {currentRoll?.busted && (
                        <span className="ml-2 text-danger font-semibold">BUST!</span>
                    )}
                    {!currentRoll?.busted && (
                        <span className="ml-2">
                            Dice: <span className="font-bold">{currentRoll?.dice_value}</span>
                        </span>
                    )}
                </div>
            </div>

            {currentRoll && (
                <>
                    <GreedyPigRoundView roll={currentRoll} allPlayers={players} />
                    <GreedyPigProgressBar roll={currentRoll} allPlayers={players} />
                </>
            )}

            <div className="flex justify-center items-center gap-6 mt-6">
                <button
                    onClick={handlePrevious}
                    disabled={isFirst}
                    className="px-6 py-3 text-lg rounded-lg bg-ui-lighter hover:bg-ui-light disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    &larr;
                </button>
                <span className="text-lg text-ui-dark">
                    Roll {globalRollIndex + 1} of {totalRolls}
                </span>
                <button
                    onClick={handleNext}
                    disabled={isLast}
                    className="px-6 py-3 text-lg rounded-lg bg-ui-lighter hover:bg-ui-light disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    &rarr;
                </button>
            </div>

            {currentPlayerFeedback.length > 0 && (
                <GreedyPigPlayerFeedback playerData={currentPlayerFeedback} />
            )}

            {isLast && feedback.final_results && (
                <div className="mt-6 p-4 bg-ui-lighter rounded-lg">
                    <h3 className="text-lg font-bold text-ui-dark mb-3">Final Results</h3>
                    <div className="space-y-1">
                        {Object.entries(feedback.final_results)
                            .sort(([, a], [, b]) => b - a)
                            .map(([player, points]) => (
                                <div key={player} className="flex justify-between text-ui-dark">
                                    <span className="font-medium">{player}</span>
                                    <span className="font-bold">{points} pts</span>
                                </div>
                            ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default GreedyPigFeedback;
