// CodeEditor.jsx
import React, { useMemo } from 'react';
import Editor from "@monaco-editor/react";

/**
 * Monaco wrapper with the project's editor defaults.
 *
 * Two modes, picked by which content prop the caller passes:
 *
 * - Uncontrolled (`defaultCode`, no `code`): Monaco owns the buffer and the
 *   caller reads it from a ref / onCodeChange. Use this anywhere a student
 *   types continuously. With `value` undefined the library's sync effect
 *   short-circuits, so it can never rewrite the model underneath the caret —
 *   its resync does executeEdits over the full range with
 *   forceMoveMarkers: true, which drags the cursor to the end of the file if
 *   a keystroke lands between React's commit and that passive effect.
 * - Controlled (`code`): React owns the buffer. Fine for forms whose editors
 *   are edited in short bursts (the Admin authoring pages).
 */
function CodeEditor({ code, defaultCode, onCodeChange, onMount, height, options, language }) {
    // Memoised so Editor's own memo can hit — a fresh options object makes the
    // library run updateOptions on every render of the parent.
    const editorOptions = useMemo(() => ({
        minimap: { enabled: false },
        scrollbar: {
            vertical: 'auto',
            horizontal: 'auto'
        },
        fontSize: 14,
        lineNumbers: 'on',
        folding: true,
        automaticLayout: true,
        scrollBeyondLastLine: false,
        ...options
    }), [options]);

    return (
        <div className="h-full flex flex-col">
            {/* Add 10px padding div with same color as Monaco editor */}
            <div className="h-[10px] bg-[#1e1e1e]"></div>
            <Editor
                height={height ?? "calc(100% - 10px)"}
                width="100%"
                theme="vs-dark"
                defaultLanguage={language ?? "python"}
                value={code}
                defaultValue={defaultCode}
                onChange={onCodeChange}
                onMount={onMount}
                options={editorOptions}
            />
        </div>
    );
}

export default CodeEditor;
