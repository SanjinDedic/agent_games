// FeedbackDisplay.jsx
import React, { useState, useEffect } from 'react';
import LessonMarkdown from '../Lesson/LessonMarkdown';

/**
 * Shared submission-page panel: a collapsible markdown instructions section on
 * top of a results area. The results content itself is supplied as children so
 * each page decides how to render its results (game outcomes, exercise test
 * cases, ...) — this component only handles the loading/empty/results states.
 * `hintsPanel` (optional) renders between the instructions and the results —
 * the exercise page uses it for its condensed hints panel.
 * Instructions render through LessonMarkdown, so they get syntax
 * highlighting, lesson:// links, and runnable ```python-run blocks.
 */
function FeedbackDisplay({
    instructions,
    instructionsTitle = "Game Instructions",
    hintsPanel,
    hasResults,
    isLoading,
    collapseInstructions,
    emptyTitle = "Submit your code to see results here",
    emptySubtitle = "Results will show how your agent performs against others",
    children,
}) {
    // Start with instructions open by default
    const [showInstructions, setShowInstructions] = useState(true);

    // Collapse instructions when code is submitted and output is received
    useEffect(() => {
        if (collapseInstructions) {
            setShowInstructions(false);
        }
    }, [collapseInstructions]);

    return (
        <div className="p-3 h-full overflow-y-auto">
            {/* Instructions Collapsible Panel */}
            {instructions && (
                <div className="mb-3 bg-white rounded-lg shadow border border-ui-light/30">
                    <button
                        onClick={() => setShowInstructions(!showInstructions)}
                        className="w-full flex items-center justify-between py-2 px-3 bg-primary text-white hover:bg-primary-hover transition-colors rounded-t-lg"
                    >
                        <span className="font-medium">{instructionsTitle}</span>
                        <span>{showInstructions ? '▲' : '▼'}</span>
                    </button>

                    {showInstructions && (
                        <div className="p-3 max-h-[550px] overflow-y-auto">
                            <LessonMarkdown content={instructions} />
                        </div>
                    )}
                </div>
            )}

            {/* Optional hints panel, between the instructions and results */}
            {hintsPanel}

            {/* Results & Feedback Area */}
            <div className="bg-white rounded-lg shadow p-3">
                <h2 className="text-xl font-bold text-ui-dark mb-3">
                    Results & Feedback
                </h2>

                {isLoading ? (
                    <div className="flex items-center justify-center h-32">
                        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
                        <span className="ml-3 text-ui-dark">Processing submission...</span>
                    </div>
                ) : hasResults ? (
                    <div>{children}</div>
                ) : (
                    <div className="text-center p-8 text-ui">
                        <p>{emptyTitle}</p>
                        <p className="text-sm mt-2">{emptySubtitle}</p>
                    </div>
                )}
            </div>
        </div>
    );
}

export default FeedbackDisplay;
