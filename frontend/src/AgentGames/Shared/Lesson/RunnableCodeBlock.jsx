import React, { useCallback, useEffect, useRef, useState } from 'react';
import CodeEditor from '../Submission/CodeEditor';
import usePyodideSnippetRun from '../hooks/usePyodideSnippetRun';
import { ensureRunner } from '../../../pyodide/exerciseRunnerClient';

// The editor grows with its content instead of scrolling internally (bad UX
// for a few added lines), up to a cap past which a genuinely large paste
// scrolls rather than taking over the modal.
const MIN_EDITOR_HEIGHT = 60;
const MAX_EDITOR_HEIGHT = 400;

const clampHeight = (px) =>
  Math.min(MAX_EDITOR_HEIGHT, Math.max(MIN_EDITOR_HEIGHT, px));

// A pre-mount estimate so the first paint is close to the final size and
// doesn't visibly jump when Monaco reports its real content height.
const estimateHeight = (text) =>
  clampHeight(text.split('\n').length * 19 + 20);

// Whitespace-tolerant form mirroring the worker's _normalize_output: strip
// trailing whitespace per line and tolerate one trailing newline, so a
// student isn't failed by an invisible trailing space.
const normalizeOutput = (text) => {
  const lines = (text ?? '').split('\n').map((line) => line.replace(/\s+$/, ''));
  if (lines.length && lines[lines.length - 1] === '') lines.pop();
  return lines.join('\n');
};

// Module-level so the object identity is stable: a fresh options object makes
// @monaco-editor/react run updateOptions on every render of this block, and
// these re-render on their own (auto-grow, run results).
const EDITOR_OPTIONS = {
  scrollbar: {
    vertical: 'auto',
    horizontal: 'auto',
    // Small editors inside a scrollable modal must not trap the wheel.
    alwaysConsumeMouseWheel: false,
  },
};

/**
 * One ```python-run block from a lesson: a small editable Monaco editor with
 * Run / Reset buttons. Run executes the (possibly edited) code Pyodide-first
 * in the browser (falling back to the sandboxed Celery worker only when
 * Pyodide can't run) and shows its stdout — or its traceback, which is just
 * as instructive. Nothing is stored server-side.
 *
 * When `expectedOutput` is set (an ```output-mark block), the block is a
 * self-checking mini-task: the run's stdout is compared against the target
 * and a match earns an instant green tick. The check is purely client-side —
 * the target is authored in the lesson content, so there is nothing to store
 * or hide; it is instant feedback, not assessment.
 */
function RunnableCodeBlock({ initialCode, expectedOutput = null }) {
  const { runSnippet } = usePyodideSnippetRun();
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);
  // Only tracks whether Reset has anything to do — flipped on the first edit,
  // not on every keystroke, so typing still costs no render of this block.
  const [edited, setEdited] = useState(false);

  // The editor is uncontrolled (see CodeEditor): Monaco owns the buffer, this
  // ref shadows it for Run, and Reset writes back through the editor handle.
  const codeRef = useRef(initialCode);
  const editorRef = useRef(null);

  const [editorHeight, setEditorHeight] = useState(() =>
    estimateHeight(initialCode)
  );

  // Warm-boot Pyodide as soon as a runnable block is on screen, so the
  // first Run doesn't pay the runtime's load latency. Safe to call from
  // every block — the runner is a shared singleton.
  useEffect(() => {
    ensureRunner();
  }, []);

  const handleCodeChange = useCallback((value) => {
    codeRef.current = value ?? '';
    // React bails out when the value is unchanged, so this renders once.
    setEdited(true);
  }, []);

  // Auto-grow the editor to fit its content: Monaco fires this on every edit
  // (Enter, paste, delete), so the block expands as the student types and
  // shrinks back if lines are removed — no internal scrollbar until the cap.
  const handleEditorMount = useCallback((editor) => {
    editorRef.current = editor;
    const applyHeight = () =>
      setEditorHeight(clampHeight(editor.getContentHeight()));
    editor.onDidContentSizeChange(applyHeight);
    applyHeight();
  }, []);

  const graded = expectedOutput != null;
  const targetText = graded ? normalizeOutput(expectedOutput) : '';
  const passed =
    graded &&
    result?.status === 'success' &&
    normalizeOutput(result.stdout) === targetText;

  const handleRun = async () => {
    setRunning(true);
    setResult(null);
    setError(null);
    const response = await runSnippet(codeRef.current);
    setRunning(false);
    if (response.success) {
      setResult(response.data);
    } else {
      // Rate limit / network failure — render in place, don't toast.
      setError(response.error);
    }
  };

  const handleReset = () => {
    codeRef.current = initialCode;
    editorRef.current?.setValue(initialCode);
    setEdited(false);
    setResult(null);
    setError(null);
  };

  return (
    <div
      className={`my-4 border rounded-md overflow-hidden not-prose transition-colors duration-200 ${
        passed ? 'border-green-500' : 'border-gray-300'
      }`}
    >
      {graded && targetText !== '' && (
        <div className="px-3 py-2 bg-blue-50 border-b border-gray-300 text-sm text-gray-700">
          <span className="font-medium">🎯 Goal — make it print exactly:</span>
          <pre className="mt-1 bg-white border border-gray-200 rounded px-2 py-1 text-xs text-gray-800 overflow-x-auto m-0 whitespace-pre-wrap">
            {targetText}
          </pre>
        </div>
      )}
      <CodeEditor
        defaultCode={initialCode}
        onCodeChange={handleCodeChange}
        onMount={handleEditorMount}
        height={`${editorHeight}px`}
        options={EDITOR_OPTIONS}
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
          disabled={running || (!edited && !result && !error)}
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
                No output add a print(), or call the function that contains the print().
              </div>
            )}
        </div>
      )}
      {graded && result?.status === 'success' && (
        <div
          className={`px-3 py-2 text-sm font-medium border-t border-gray-300 flex items-center gap-2 ${
            passed ? 'bg-green-600 text-white' : 'bg-amber-50 text-amber-800'
          }`}
        >
          {passed ? (
            <>✓ Completed — your output matches the goal.</>
          ) : (
            <>Not quite yet — your output doesn't match the goal. Compare them and try again.</>
          )}
        </div>
      )}
    </div>
  );
}

export default RunnableCodeBlock;
