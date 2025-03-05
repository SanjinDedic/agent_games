// CodeEditor.jsx
import React from 'react';
import Editor from "@monaco-editor/react";

function CodeEditor({ code, onCodeChange, onMount }) {
    const editorOptions = {
        minimap: { enabled: false },
        scrollbar: {
            vertical: 'auto',
            horizontal: 'auto'
        },
        fontSize: 14,
        lineNumbers: 'on',
        folding: true,
        automaticLayout: true,
        scrollBeyondLastLine: false
    };

    return (
        <div className="h-full">
            <Editor
                height="100%"
                width="100%"
                theme="vs-dark"
                defaultLanguage="python"
                value={code}
                onChange={onCodeChange}
                onMount={onMount}
                options={editorOptions}
            />
        </div>
    );
}

export default CodeEditor;