import React, { useState } from "react";
import LessonMarkdown from "../Shared/Lesson/LessonMarkdown";

/**
 * Condensed hints panel for an exercise: a single collapsed bar until the
 * student opens it, and hints inside are revealed one at a time, in order,
 * so nobody gets spoiled past the nudge they asked for. Renders nothing
 * when the exercise has no hints. Hints are Markdown, rendered through
 * LessonMarkdown so they can carry lesson:// links too.
 */
function ExerciseHints({ hints }) {
    const [isOpen, setIsOpen] = useState(false);
    const [revealedCount, setRevealedCount] = useState(0);

    if (!hints || hints.length === 0) return null;

    return (
        <div className="mb-3 bg-white rounded-lg shadow border border-ui-light/30">
            <style>{`
                .hint-markdown p:last-child, .hint-markdown ul:last-child, .hint-markdown ol:last-child {
                    margin-bottom: 0;
                }
            `}</style>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`w-full flex items-center justify-between py-2 px-3 bg-amber-500 text-white hover:bg-amber-600 transition-colors rounded-t-lg ${
                    isOpen ? "" : "rounded-b-lg"
                }`}
            >
                <span className="font-medium">
                    💡 Hints ({revealedCount}/{hints.length} shown)
                </span>
                <span>{isOpen ? "▲" : "▼"}</span>
            </button>

            {isOpen && (
                <div className="p-3 space-y-3">
                    {hints.slice(0, revealedCount).map((hint, index) => (
                        <div key={index} className="flex gap-2 text-sm">
                            <span className="font-semibold text-ui-dark/60 flex-shrink-0">
                                {index + 1}.
                            </span>
                            <div className="hint-markdown min-w-0">
                                <LessonMarkdown content={hint} />
                            </div>
                        </div>
                    ))}
                    {revealedCount < hints.length && (
                        <button
                            onClick={() => setRevealedCount(revealedCount + 1)}
                            className="w-full py-2 px-3 text-sm rounded border border-dashed border-amber-500 text-amber-700 hover:bg-amber-50 transition-colors"
                        >
                            {revealedCount === 0
                                ? "Show a hint"
                                : "Show the next hint"}
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}

export default ExerciseHints;
