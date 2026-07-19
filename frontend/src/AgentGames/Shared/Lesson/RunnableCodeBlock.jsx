import React, { useState } from 'react';
import CodeEditor from '../Submission/CodeEditor';
import useLessonAPI from '../hooks/useLessonAPI';

/**
 * One ```python-run block from a lesson: a small editable Monaco editor with
 * Run / Reset buttons. Run executes the (possibly edited) code in the
 * sandboxed exercise worker and shows its stdout — or its traceback, which
 * is just as instructive. Nothing is stored server-side.
 */
function RunnableCodeBlock({ initialCode }) {
  const { runSnippet } = useLessonAPI();
  const [code, setCode] = useState(initialCode);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);

  const lineCount = initialCode.split('\n').length;
  const editorHeight = `${Math.min(400, Math.max(60, lineCount * 19 + 20))}px`;

  const handleRun = async () => {
    setRunning(true);
    setResult(null);
    setError(null);
    const response = await runSnippet(code);
    setRunning(false);
    if (response.success) {
      setResult(response.data);
    } else {
      // Rate limit / network failure — render in place, don't toast.
      setError(response.error);
    }
  };

  const handleReset = () => {
    setCode(initialCode);
    setResult(null);
    setError(null);
  };

  return (
    <div className="my-4 border border-gray-300 rounded-md overflow-hidden not-prose">
      <CodeEditor
        code={code}
        onCodeChange={(value) => setCode(value ?? '')}
        height={editorHeight}
        options={{
          scrollbar: {
            vertical: 'auto',
            horizontal: 'auto',
            // Small editors inside a scrollable modal must not trap the wheel.
            alwaysConsumeMouseWheel: false,
          },
        }}
      />
      <div className="flex items-center gap-2 px-3 py-2 bg-gray-100 border-t border-gray-300">
        <button
          type="button"
          onClick={handleRun}
          disabled={running}
          className={`px-3 py-1 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors duration-200 ${
            running ? 'opacity-70 cursor-not-allowed' : ''
          }`}
        >
          {running ? 'Running...' : '▶ Run'}
        </button>
        <button
          type="button"
          onClick={handleReset}
          disabled={running || (code === initialCode && !result && !error)}
          className="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors duration-200"
        >
          Reset
        </button>
        {result?.duration_ms != null && (
          <span className="ml-auto text-xs text-gray-500 font-mono">
            {result.duration_ms < 1
              ? '<1 ms'
              : `${Math.round(result.duration_ms)} ms`}
          </span>
        )}
      </div>
      {error && (
        <div className="px-3 py-2 bg-danger/10 text-danger text-sm border-t border-gray-300">
          {error}
        </div>
      )}
      {result && (
        <div className="border-t border-gray-300">
          {result.status === 'error' && result.message && (
            <div className="px-3 py-2 bg-danger text-white text-sm font-medium">
              {result.message}
            </div>
          )}
          {result.traceback && (
            <pre className="bg-[#1e1e1e] text-red-300 p-3 text-sm overflow-x-auto m-0">
              {result.traceback}
            </pre>
          )}
          {result.stdout != null && result.stdout !== '' && (
            <pre className="bg-[#1e1e1e] text-gray-100 p-3 text-sm overflow-x-auto m-0">
              {result.stdout}
            </pre>
          )}
          {result.status === 'success' &&
            (result.stdout == null || result.stdout === '') && (
              <div className="px-3 py-2 text-sm text-gray-500 bg-gray-50">
                Ran without output — add a print() to see results.
              </div>
            )}
        </div>
      )}
    </div>
  );
}

export default RunnableCodeBlock;
