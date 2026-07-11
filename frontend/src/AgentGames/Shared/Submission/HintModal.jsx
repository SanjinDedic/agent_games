import React, { useState, useEffect } from "react";

// Maps the backend hint priority (1 = critical ... 5 = minor) to a label + badge style
const PRIORITY_META = {
  1: { label: "Critical", className: "bg-danger text-white" },
  2: { label: "High", className: "bg-notice-orange text-white" },
  3: { label: "Medium", className: "bg-notice-yellowBg text-ui-dark" },
  4: { label: "Low", className: "bg-primary text-white" },
  5: { label: "Minor", className: "bg-ui-light text-ui-dark" },
};

function HintModal({ isOpen, isLoading, hint, onClose }) {
  const [showFullHint, setShowFullHint] = useState(false);

  // Reset the "reveal full hint" toggle whenever a new hint is shown
  useEffect(() => {
    setShowFullHint(false);
  }, [hint, isLoading]);

  if (!isOpen) return null;

  const priorityMeta = hint ? PRIORITY_META[hint.priority] : null;

  return (
    // Wrapper spans the right half only and ignores pointer events, so the
    // coding window on the left stays fully visible and interactive.
    <div className="fixed top-12 bottom-14 right-0 z-40 w-1/2 flex p-3 pointer-events-none">
      <div className="ml-auto w-full bg-white rounded-lg shadow-2xl border border-ui-lighter flex flex-col overflow-hidden pointer-events-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-ui-lighter bg-primary">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <span aria-hidden="true">💡</span> Hint
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-white/80 hover:text-white text-2xl leading-none"
            aria-label="Close hint"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto p-5">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-full text-ui-dark/70 gap-3">
              <div className="w-8 h-8 border-4 border-ui-lighter border-t-primary rounded-full animate-spin" />
              <p className="text-sm">Analyzing your code…</p>
            </div>
          ) : !hint ? (
            <div className="flex flex-col items-center justify-center h-full text-center gap-2">
              <span className="text-4xl" aria-hidden="true">
                ✅
              </span>
              <p className="text-ui-dark font-medium">No issues found</p>
              <p className="text-sm text-ui-dark/60">
                Your code looks good — submit when you're ready.
              </p>
            </div>
          ) : (
            <div className="space-y-5">
              {/* Priority badge */}
              {priorityMeta && (
                <span
                  className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${priorityMeta.className}`}
                >
                  {priorityMeta.label} priority
                </span>
              )}

              {/* Code location */}
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-ui-dark/50 mb-1">
                  Line {hint.line_number}
                </p>
                <pre className="bg-ui-dark text-white text-sm rounded p-3 overflow-x-auto">
                  <code>{hint.quoted_line}</code>
                </pre>
              </div>

              {/* Socratic nudge */}
              <div className="bg-notice-yellowBg rounded p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-ui-dark/60 mb-1">
                  Something to think about
                </p>
                <p className="text-ui-dark">{hint.small_hint}</p>
              </div>

              {/* Full explanation (revealed on demand) */}
              {hint.big_hint && (
                <div>
                  {showFullHint ? (
                    <div className="bg-primary/5 border border-primary/20 rounded p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-primary mb-1">
                        Full explanation
                      </p>
                      <p className="text-ui-dark whitespace-pre-wrap">
                        {hint.big_hint}
                      </p>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setShowFullHint(true)}
                      className="py-2 px-4 text-sm font-medium text-white bg-primary hover:bg-primary-hover rounded transition-colors"
                    >
                      Reveal full explanation
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default HintModal;
