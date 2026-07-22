import React from 'react';
import Editor from '@monaco-editor/react';

export const formatTimestamp = (ts) => {
  if (!ts) return '';
  const d = new Date(ts);
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

export const formatDuration = (ms) => {
  if (ms == null) return 'n/a';
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
};

/**
 * Read-only Monaco viewer with prev/next navigation through a submission
 * history. `submissions` is oldest -> newest; `index` selects the shown one.
 * `renderMeta(current)` can add extra lines under the position label.
 */
const CodeHistoryViewer = ({
  submissions,
  index,
  onIndexChange,
  renderMeta,
  language = 'python',
}) => {
  const total = submissions.length;
  const current = submissions[index];

  return (
    <div className="flex-1 bg-white rounded-lg shadow overflow-hidden flex flex-col min-h-0">
      <div className="flex-1 min-h-0">
        <Editor
          height="100%"
          defaultLanguage={language}
          theme="vs-dark"
          value={current?.code || ''}
          options={{
            readOnly: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            wordWrap: 'on',
          }}
        />
      </div>

      {total > 0 && (
        <div className="flex items-center justify-between px-4 py-2 bg-gray-100 border-t border-ui-light">
          <button
            onClick={() => index > 0 && onIndexChange(index - 1)}
            disabled={index === 0}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              index === 0
                ? 'text-gray-400 cursor-not-allowed'
                : 'text-primary hover:bg-primary hover:text-white'
            }`}
          >
            ← Prev
          </button>

          <div className="flex flex-col items-center">
            <span className="text-xs text-ui font-medium">
              Submission {index + 1} of {total}
            </span>
            <span className="text-xs text-gray-500">
              {formatTimestamp(current?.timestamp)}
            </span>
            {renderMeta ? (
              renderMeta(current)
            ) : (
              <span className="text-xs text-gray-500">
                Sim duration: {formatDuration(current?.duration_ms)}
              </span>
            )}
          </div>

          <button
            onClick={() => index < total - 1 && onIndexChange(index + 1)}
            disabled={index === total - 1}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              index === total - 1
                ? 'text-gray-400 cursor-not-allowed'
                : 'text-primary hover:bg-primary hover:text-white'
            }`}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
};

export default CodeHistoryViewer;
