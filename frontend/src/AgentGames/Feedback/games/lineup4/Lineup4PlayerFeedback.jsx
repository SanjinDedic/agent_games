import React, { useState } from 'react';

const Lineup4PlayerFeedback = ({ currentMove }) => {
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

    return (
        <div className="mt-6 mb-4">
            <div className="bg-ui-lighter rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                    <h3 className="text-lg font-medium text-ui-dark">
                        Feedback from {currentMove.player}
                    </h3>
                    {currentMove.player_feedback?.length > 0 && (
                        <button
                            onClick={() => setIsExpanded(!isExpanded)}
                            className="text-primary hover:text-primary-hover text-sm font-medium"
                        >
                            {isExpanded ? 'Show Less' : 'Show More'}
                        </button>
                    )}
                </div>

                <div className={`
                    transition-all duration-200 ease-in-out
                    ${isExpanded ? 'max-h-96' : 'h-24'}
                    ${isExpanded ? 'overflow-y-auto' : 'overflow-hidden'}
                `}>
                    {currentMove.player_feedback?.length > 0 ? (
                        <div className="space-y-2">
                            {currentMove.player_feedback.map((feedback, index) => (
                                <div key={index} className="relative">
                                    <div className="absolute top-2 right-2 flex items-center gap-2">
                                        {copySuccess && index === 0 && (
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
                                    <div className="p-2 pt-10 bg-white rounded border border-ui-light text-ui break-words font-mono text-sm whitespace-pre">
                                        {formatFeedback(feedback)}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="flex items-center h-24 text-ui">
                            No feedback available
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Lineup4PlayerFeedback;