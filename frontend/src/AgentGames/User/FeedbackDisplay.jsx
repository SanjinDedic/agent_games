// FeedbackDisplay.jsx
import React, { useState, useEffect } from 'react';
import FeedbackSelector from '../Feedback/FeedbackSelector';
import GameResultsWrapper from '../Feedback/GameResultsWrapper';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';

function FeedbackDisplay({ instructions, output, feedback, isLoading, collapseInstructions }) {
    // Start with instructions open by default
    const [showInstructions, setShowInstructions] = useState(true);

    // Collapse instructions when code is submitted and output is received
    useEffect(() => {
        if (collapseInstructions) {
            setShowInstructions(false);
        }
    }, [collapseInstructions]);

    return (
        <div className="p-4 h-full overflow-y-auto">
            {/* Instructions Collapsible Panel */}
            {instructions && (
                <div className="mb-4 bg-white rounded-lg shadow border border-ui-light/30">
                    <button
                        onClick={() => setShowInstructions(!showInstructions)}
                        className="w-full flex items-center justify-between p-3 bg-primary text-white hover:bg-primary-hover transition-colors rounded-t-lg"
                    >
                        <span className="font-medium">Game Instructions</span>
                        <span>{showInstructions ? '▲' : '▼'}</span>
                    </button>

                    {showInstructions && (
                        <div className="p-4 max-h-64 overflow-y-auto">
                            <ReactMarkdown rehypePlugins={[rehypeRaw]}>
                                {instructions}
                            </ReactMarkdown>
                        </div>
                    )}
                </div>
            )}

            {/* Results & Feedback Area */}
            <div className="bg-white rounded-lg shadow p-4">
                <h2 className="text-xl font-bold text-ui-dark mb-4">
                    Results & Feedback
                </h2>

                {isLoading ? (
                    <div className="flex items-center justify-center h-32">
                        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
                        <span className="ml-3 text-ui-dark">Processing submission...</span>
                    </div>
                ) : output ? (
                    <div>
                        <GameResultsWrapper data={output} tablevisible={true} />
                        {feedback && <FeedbackSelector feedback={feedback} />}
                    </div>
                ) : (
                    <div className="text-center p-8 text-ui">
                        <p>Submit your code to see results here</p>
                        <p className="text-sm mt-2">
                            Results will show how your agent performs against others
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}

export default FeedbackDisplay;