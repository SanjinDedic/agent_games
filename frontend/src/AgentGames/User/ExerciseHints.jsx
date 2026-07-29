import React, { useState } from "react";
import LessonMarkdown from "../Shared/Lesson/LessonMarkdown";
import useTutorialAPI from "../Shared/hooks/useTutorialAPI";

/**
 * Condensed hints panel for an exercise: a single collapsed bar until the
 * student opens it, and hints inside are revealed one at a time, in order,
 * so nobody gets spoiled past the nudge they asked for. Renders nothing
 * when the exercise has no hints. Hints are Markdown, rendered through
 * LessonMarkdown so they can carry lesson:// links too.
 *
 * Each reveal is reported to the server (fire-and-forget, repeats ignored)
 * because the teacher's concept mastery view counts a revealed hint as extra
 * effort. `exerciseId` is optional so the admin preview, which has no saved
 * exercise to attribute a reveal to, can still render hints.
 */
function ExerciseHints({ hints, exerciseId }) {
    const [isOpen, setIsOpen] = useState(false);
    const [revealedCount, setRevealedCount] = useState(0);
    const { recordHintReveal } = useTutorialAPI();

    const revealNext = () => {
        const hintIndex = revealedCount;
        setRevealedCount(hintIndex + 1);
        if (exerciseId != null) {
            recordHintReveal(exerciseId, hintIndex);
        }
    };

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
                            onClick={revealNext}
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
