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
        <div className="h-full flex flex-col">
            {/* Add 10px padding div with same color as Monaco editor */}
            <div className="h-[10px] bg-[#1e1e1e]"></div>
            <Editor
                height="calc(100% - 10px)"
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