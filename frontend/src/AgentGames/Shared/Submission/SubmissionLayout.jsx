import React from 'react';
import { useSelector } from 'react-redux';
import { selectImmersiveMode } from '../../../slices/settingsSlice';

/**
 * Shared page scaffold for code-submission pages: editor on the left half,
 * instructions/results panel on the right, a fixed footer toolbar at the
 * bottom. Modals (submission history, hints, ...) go in as children.
 *
 * In immersive mode (toggled from CombinedFooter) the navbar is hidden, so
 * the top padding goes away and the panes grow by the navbar's 48px.
 *
 * `editorDrawer` (optional) docks below the editor inside the left pane —
 * the exercise page uses it for the program-output drawer.
 */
function SubmissionLayout({ editor, editorDrawer, panel, footer, children }) {
    const isImmersive = useSelector(selectImmersiveMode);
    const paneHeight = isImmersive
        ? "h-[calc(100vh-64px)]"
        : "h-[calc(100vh-112px)]";

    return (
        <div className={`min-h-screen ${isImmersive ? "pt-0" : "pt-12"} flex flex-col bg-white`}>
            <div className="flex flex-1 overflow-hidden pb-14">
                {/* Left side - Code Editor */}
                <div className={`w-1/2 ${paneHeight} border-r border-[#1e1e1e] border-t-0 bg-[#1e1e1e] ${editorDrawer ? "flex flex-col" : ""}`}>
                    {editorDrawer ? <div className="flex-1 min-h-0">{editor}</div> : editor}
                    {editorDrawer}
                </div>

                {/* Right side - Instructions & Results */}
                <div className={`w-1/2 flex flex-col ${paneHeight}`}>
                    <div className="flex-1 overflow-auto">{panel}</div>
                </div>
            </div>

            {footer}

            {children}
        </div>
    );
}

export default SubmissionLayout;
