import React, { useState } from 'react';

/**
 * Slim output drawer docked under the code editor, showing whatever the
 * submitted code printed (the worker merges stderr into the same stream).
 * Three sizes: collapsed (header bar only), default (~3 lines) and expanded.
 *
 * `stdout` is tri-state: undefined means no run yet, null/"" means the code
 * ran without printing, a non-empty string is the captured output.
 */
function OutputDrawer({ stdout, isLoading }) {
    const [size, setSize] = useState("default");
    const isCollapsed = size === "collapsed";
    const isExpanded = size === "expanded";

    let placeholder = null;
    if (isLoading) {
        placeholder = "Running…";
    } else if (stdout === undefined) {
        placeholder = "Output from print() will appear here.";
    } else if (!stdout) {
        placeholder = "Ran without output — add a print() to see results.";
    }

    return (
        <div className="shrink-0 border-t border-[#333] bg-[#1e1e1e]">
            <div className="flex items-center px-3 py-1 bg-[#252526] text-gray-400 text-xs font-medium uppercase tracking-wide select-none">
                <button
                    type="button"
                    className="flex-1 text-left hover:text-gray-200"
                    onClick={() => setSize(isCollapsed ? "default" : "collapsed")}
                >
                    Output {isCollapsed ? "▲" : "▼"}
                </button>
                {!isCollapsed && (
                    <button
                        type="button"
                        className="hover:text-gray-200"
                        title={isExpanded ? "Shrink output panel" : "Expand output panel"}
                        onClick={() => setSize(isExpanded ? "default" : "expanded")}
                    >
                        {isExpanded ? "⤡" : "⤢"}
                    </button>
                )}
            </div>
            {!isCollapsed && (
                <pre
                    className={`m-0 px-3 py-2 font-mono text-sm leading-5 whitespace-pre-wrap text-gray-100 bg-[#1e1e1e] overflow-y-auto ${
                        isExpanded ? "h-[40vh]" : "max-h-[76px]"
                    }`}
                >
                    {placeholder ? (
                        <span className="text-gray-500 italic">{placeholder}</span>
                    ) : (
                        stdout
                    )}
                </pre>
            )}
        </div>
    );
}

export default OutputDrawer;
