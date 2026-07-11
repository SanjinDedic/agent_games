import React from 'react';

function CombinedFooter({
    statusItems = [],
    onSubmit,
    onGetHint,
    onLoadLast,
    onReset,
    onShowSubmissions,
    isLoading,
    allowHint,
    isGeneratingHint,
    hasLastSubmission,
    hasStarterCode
}) {
    return (
      <div className="fixed bottom-0 left-0 right-0 z-10 w-full bg-ui shadow-md">
        {/* Main status bar */}
        <div className="flex items-center justify-between px-6 py-3 text-white">
          {/* Left side - Control buttons with same spacing as info */}
          <div className="flex space-x-8">
            <button
              onClick={onSubmit}
              disabled={isLoading}
              className="py-2 px-4 text-base font-medium text-white bg-primary hover:bg-primary-hover disabled:bg-ui-light rounded transition-colors"
            >
              {isLoading ? "Processing..." : "Submit Code"}
            </button>

            { allowHint ?
              <button
                onClick={onGetHint}
                disabled={isLoading}
                className="py-2 px-4 text-base font-medium text-white bg-success hover:bg-success-hover disabled:bg-ui-light rounded transition-colors"
              >
                {isGeneratingHint ? "Getting Hint..." : "Get Hint"}
              </button> : null
            }

            <button
              onClick={onLoadLast}
              disabled={!hasLastSubmission || isLoading}
              className="py-2 px-4 text-base font-medium text-white bg-league-blue hover:bg-league-hover disabled:bg-ui-light rounded transition-colors"
            >
              Last Submission
            </button>

            <button
              onClick={onReset}
              disabled={isLoading || !hasStarterCode}
              className="py-2 px-4 text-base font-medium text-white bg-notice-orange hover:bg-notice-orange/90 disabled:bg-ui-light rounded transition-colors"
            >
              Reset Code
            </button>

            <button
              onClick={onShowSubmissions}
              disabled={isLoading}
              className="py-2 px-4 text-base font-medium text-white bg-league-blue hover:bg-league-hover disabled:bg-ui-light rounded transition-colors"
            >
              My Submissions
            </button>
          </div>

          {/* Right side - Status info */}
          <div className="flex space-x-8">
            {statusItems
              .filter((item) => item.value)
              .map((item) => (
                <div key={item.label} className="text-lg font-medium">
                  <span className="text-ui-light">{item.label}:</span> {item.value}
                </div>
              ))}
          </div>
        </div>
      </div>
    );
}

export default CombinedFooter;
