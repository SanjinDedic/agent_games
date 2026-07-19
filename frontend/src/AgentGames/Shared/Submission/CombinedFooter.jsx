import React from 'react';
import useImmersiveMode from '../hooks/useImmersiveMode';

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
    const { isImmersive, toggleImmersive } = useImmersiveMode();

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

          {/* Right side - Status info + immersive mode */}
          <div className="flex items-center space-x-8">
            {statusItems
              .filter((item) => item.value)
              .map((item) => (
                <div key={item.label} className="text-lg font-medium">
                  <span className="text-ui-light">{item.label}:</span> {item.value}
                </div>
              ))}

            <button
              onClick={toggleImmersive}
              title={
                isImmersive
                  ? "Exit immersive mode (Esc)"
                  : "Fullscreen with the navbar hidden"
              }
              className="flex items-center gap-2 py-2 px-4 text-base font-medium text-white bg-ui-dark hover:bg-ui-hover rounded transition-colors"
            >
              {isImmersive ? (
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
                  <path d="M8 3v3a2 2 0 0 1-2 2H3" />
                  <path d="M21 8h-3a2 2 0 0 1-2-2V3" />
                  <path d="M3 16h3a2 2 0 0 1 2 2v3" />
                  <path d="M16 21v-3a2 2 0 0 1 2-2h3" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
                  <path d="M8 3H5a2 2 0 0 0-2 2v3" />
                  <path d="M21 8V5a2 2 0 0 0-2-2h-3" />
                  <path d="M3 16v3a2 2 0 0 0 2 2h3" />
                  <path d="M16 21h3a2 2 0 0 0 2-2v-3" />
                </svg>
              )}
              {isImmersive ? "Exit" : "Immersive"}
            </button>
          </div>
        </div>
      </div>
    );
}

export default CombinedFooter;
