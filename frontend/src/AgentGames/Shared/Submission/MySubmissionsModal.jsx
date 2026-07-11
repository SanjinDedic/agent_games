import React from "react";

function formatTimestamp(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatDuration(ms) {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

function MySubmissionsModal({ isOpen, onClose, submissions, isLoading, onSelect }) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-ui-lighter">
          <h2 className="text-xl font-bold text-ui-dark">My Submissions</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-ui-dark/60 hover:text-ui-dark text-2xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-auto">
          {isLoading ? (
            <div className="p-6 text-center text-ui-dark/70">Loading…</div>
          ) : submissions.length === 0 ? (
            <div className="p-6 text-center text-ui-dark/70">
              No submissions yet.
            </div>
          ) : (
            <ul className="divide-y divide-ui-lighter">
              {submissions.map((sub, idx) => (
                <li key={sub.id ?? idx}>
                  <button
                    type="button"
                    onClick={() => onSelect(sub)}
                    className="w-full text-left px-6 py-3 hover:bg-ui-lighter/50 transition-colors flex items-center justify-between gap-4"
                  >
                    <div className="flex flex-col">
                      <span className="font-mono text-sm text-ui-dark">
                        {formatTimestamp(sub.timestamp)}
                      </span>
                      <span className="text-xs text-ui-dark/60">
                        Submission #{sub.id}
                        {idx === 0 ? " · latest" : ""}
                      </span>
                    </div>
                    <span className="text-sm text-ui-dark/70 font-mono">
                      {formatDuration(sub.duration_ms)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="px-6 py-3 border-t border-ui-lighter text-right">
          <button
            type="button"
            onClick={onClose}
            className="py-2 px-4 text-sm font-medium text-white bg-ui-light hover:bg-ui rounded transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default MySubmissionsModal;
