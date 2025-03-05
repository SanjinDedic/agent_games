// ControlPanel.jsx
import React from 'react';

function ControlPanel({
    onSubmit,
    onLoadLast,
    onReset,
    isLoading,
    hasLastSubmission,
    hasStarterCode
}) {
    return (
        <div className="p-4 bg-ui-lighter border-t border-ui-light">
            <div className="flex gap-3 justify-end">
                <button
                    onClick={onSubmit}
                    disabled={isLoading}
                    className="py-3 px-5 text-lg font-medium text-white bg-primary hover:bg-primary-hover disabled:bg-ui-light rounded-lg transition-colors"
                >
                    {isLoading ? 'Processing...' : 'Submit Code'}
                </button>

                <button
                    onClick={onLoadLast}
                    disabled={!hasLastSubmission || isLoading}
                    className="py-3 px-5 text-lg font-medium text-white bg-league-blue hover:bg-league-hover disabled:bg-ui-light rounded-lg transition-colors"
                >
                    Last Submission
                </button>

                <button
                    onClick={onReset}
                    disabled={isLoading || !hasStarterCode}
                    className="py-3 px-5 text-lg font-medium text-white bg-notice-orange hover:bg-notice-orange/90 disabled:bg-ui-light rounded-lg transition-colors"
                >
                    Reset Code
                </button>
            </div>
        </div>
    );
}

export default ControlPanel;