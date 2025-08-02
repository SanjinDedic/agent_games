import React, { useState } from 'react';

const ArenaChampionsPlayerFeedback = ({ currentTurn, battleData, feedback }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [copySuccess, setCopySuccess] = useState('');

    const formatFeedback = (feedback) => {
        if (typeof feedback === 'string') {
            return feedback;
        }
        try {
            return JSON.stringify(feedback, null, 2);
        } catch (error) {
            return 'Error displaying feedback';
        }
    };

    const handleCopy = async (text) => {
        try {
            await navigator.clipboard.writeText(text);
            setCopySuccess('Copied!');
            setTimeout(() => setCopySuccess(''), 2000);
        } catch (err) {
            setCopySuccess('Failed to copy');
            setTimeout(() => setCopySuccess(''), 2000);
        }
    };

    // Get player feedback from the feedback structure
    const getPlayerFeedbacks = () => {
        const feedbacks = [];
        
        // Check if we have player feedback data in the feedback structure
        if (feedback?.player_feedback) {
            // Look for feedback from both players for this specific turn
            Object.entries(feedback.player_feedback).forEach(([playerName, playerFeedbackList]) => {
                // Find feedback for this specific turn
                const turnFeedback = playerFeedbackList.find(fb => 
                    fb.turn === currentTurn.turn
                );
                
                if (turnFeedback && turnFeedback.messages && turnFeedback.messages.length > 0) {
                    feedbacks.push({
                        player: playerName,
                        feedback: turnFeedback.messages
                    });
                }
            });
        }
        
        return feedbacks;
    };

    const playerFeedbacks = getPlayerFeedbacks();

    if (playerFeedbacks.length === 0) {
        return (
            <div className="mt-6 mb-4">
                <div className="bg-ui-lighter rounded-lg p-4">
                    <h3 className="text-lg font-medium text-ui-dark mb-2">
                        Player Feedback
                    </h3>
                    <div className="flex items-center h-16 text-ui">
                        No feedback available for this turn
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="mt-6 mb-4">
            <div className="bg-ui-lighter rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                    <h3 className="text-lg font-medium text-ui-dark">
                        Player Feedback - Turn {currentTurn.turn}
                    </h3>
                    <button
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="text-primary hover:text-primary-hover text-sm font-medium"
                    >
                        {isExpanded ? 'Show Less' : 'Show More'}
                    </button>
                </div>

                <div className={`
                    transition-all duration-200 ease-in-out
                    ${isExpanded ? 'max-h-96' : 'max-h-32'}
                    overflow-y-auto
                `}>
                    <div className="space-y-4">
                        {playerFeedbacks.map((playerFeedback, playerIndex) => (
                            <div key={playerIndex} className="space-y-2">
                                <h4 className="font-medium text-ui-dark flex items-center gap-2">
                                    <span className={playerFeedback.player === battleData.player1 ? 'text-primary' : 'text-danger'}>
                                        {playerFeedback.player}
                                    </span>
                                    <span className="text-ui">Feedback:</span>
                                </h4>
                                
                                {Array.isArray(playerFeedback.feedback) ? (
                                    playerFeedback.feedback.map((feedback, feedbackIndex) => (
                                        <div key={feedbackIndex} className="relative">
                                            <div className="absolute top-2 right-2 flex items-center gap-2">
                                                {copySuccess && (
                                                    <span className="text-xs text-success font-medium">
                                                        {copySuccess}
                                                    </span>
                                                )}
                                                <button
                                                    onClick={() => handleCopy(formatFeedback(feedback))}
                                                    className="bg-white hover:bg-ui-lighter text-ui-dark rounded px-2 py-1 text-xs font-medium border border-ui-light transition-colors duration-200"
                                                >
                                                    Copy
                                                </button>
                                            </div>
                                            <div className="p-3 pt-10 bg-white rounded border border-ui-light text-ui break-words font-mono text-sm whitespace-pre-wrap">
                                                {formatFeedback(feedback)}
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="relative">
                                        <div className="absolute top-2 right-2 flex items-center gap-2">
                                            {copySuccess && (
                                                <span className="text-xs text-success font-medium">
                                                    {copySuccess}
                                                </span>
                                            )}
                                            <button
                                                onClick={() => handleCopy(formatFeedback(playerFeedback.feedback))}
                                                className="bg-white hover:bg-ui-lighter text-ui-dark rounded px-2 py-1 text-xs font-medium border border-ui-light transition-colors duration-200"
                                            >
                                                Copy
                                            </button>
                                        </div>
                                        <div className="p-3 pt-10 bg-white rounded border border-ui-light text-ui break-words font-mono text-sm whitespace-pre-wrap">
                                            {formatFeedback(playerFeedback.feedback)}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Turn Actions Summary */}
                <div className="mt-4 pt-3 border-t border-ui-light">
                    <h4 className="font-medium text-ui-dark mb-2">Turn Actions:</h4>
                    <div className="flex justify-between text-sm">
                        <div className="flex items-center gap-2">
                            <span className="text-primary font-medium">{battleData.player1}:</span>
                            <span className="capitalize">{currentTurn.actions[battleData.player1]}</span>
                            {currentTurn[`${battleData.player1}_damage`] && (
                                <span className="text-danger">({currentTurn[`${battleData.player1}_damage`]} dmg)</span>
                            )}
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-danger font-medium">{battleData.player2}:</span>
                            <span className="capitalize">{currentTurn.actions[battleData.player2]}</span>
                            {currentTurn[`${battleData.player2}_damage`] && (
                                <span className="text-danger">({currentTurn[`${battleData.player2}_damage`]} dmg)</span>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ArenaChampionsPlayerFeedback;