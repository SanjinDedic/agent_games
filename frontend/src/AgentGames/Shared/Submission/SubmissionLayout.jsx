import React from 'react';

/**
 * Shared page scaffold for code-submission pages: editor on the left half,
 * instructions/results panel on the right, a fixed footer toolbar at the
 * bottom. Modals (submission history, hints, ...) go in as children.
 */
function SubmissionLayout({ editor, panel, footer, children }) {
    return (
        <div className="min-h-screen pt-12 flex flex-col bg-white">
            <div className="flex flex-1 overflow-hidden pb-14">
                {/* Left side - Code Editor */}
                <div className="w-1/2 h-[calc(100vh-112px)] border-r border-[#1e1e1e] border-t-0 bg-[#1e1e1e]">
                    {editor}
                </div>

                {/* Right side - Instructions & Results */}
                <div className="w-1/2 flex flex-col h-[calc(100vh-112px)]">
                    <div className="flex-1 overflow-auto">{panel}</div>
                </div>
            </div>

            {footer}

            {children}
        </div>
    );
}

export default SubmissionLayout;
