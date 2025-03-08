// FeedbackDisplay.jsx
import React, { useState, useEffect } from 'react';
import FeedbackSelector from '../Feedback/FeedbackSelector';
import GameResultsWrapper from '../Feedback/GameResultsWrapper';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';

function FeedbackDisplay({ instructions, output, feedback, isLoading, collapseInstructions }) {
    // Start with instructions open by default
    const [showInstructions, setShowInstructions] = useState(true);

    // Markdown styling from PureMarkdown component
    const markdownStyles = `
        .markdown-content {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: #333;
            width: 100%;
            padding: 0;
        }
        .markdown-content h1, .markdown-content h2, .markdown-content h3, .markdown-content h4, .markdown-content h5, .markdown-content h6 {
            margin-top: 12px;
            margin-bottom: 4px;
            font-weight: 600;
            line-height: 1.25;
        }
        .markdown-content h1 {
            font-size: 1.8em;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.2em;
        }
        .markdown-content h2 {
            font-size: 1.3em;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.1em;
        }
        .markdown-content h3 {
            font-size: 1.25em;
        }
        .markdown-content p, .markdown-content ul, .markdown-content ol {
            margin-top: 0;
            margin-bottom: 16px;
        }
        .markdown-content code {
            padding: 0.2em 0.4em;
            margin: 0;
            font-size: 100%; 
            background-color: rgba(27,31,35,0.05);
            border-radius: 3px;
        }
        .markdown-content pre {
            padding: 16px;
            overflow: auto;
            font-size: 100%; 
            line-height: 1.45;
            background-color: #f6f8fa;
            border-radius: 3px;
        }
        .markdown-content pre code {
            font-size: 12px !important;
            line-height: 1.2 !important;
            display: inline;
            max-width: auto;
            padding: 0;
            margin: 0;
            overflow: visible;
            line-height: inherit;
            word-wrap: normal;
            background-color: transparent;
            border: 0; 
        }
    `;

    // Collapse instructions when code is submitted and output is received
    useEffect(() => {
        if (collapseInstructions) {
            setShowInstructions(false);
        }
    }, [collapseInstructions]);

    return (
        <div className="p-4 h-full overflow-y-auto">
            {/* Add the markdown styles */}
            <style>{markdownStyles}</style>

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
                        <div className="p-4 max-h-[550px] overflow-y-auto">
                            <div className="markdown-content">
                                <ReactMarkdown rehypePlugins={[rehypeRaw]}>
                                    {instructions}
                                </ReactMarkdown>
                            </div>
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