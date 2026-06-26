import React from 'react';
import { useSelector } from 'react-redux';
import { selectCurrentUser } from '../../slices/authSlice';

function CombinedFooter({
    team,
    game,
    league,
    isDemo,
    onSubmit,
    onGetHint,
    onLoadLast,
    onReset,
    onShowSubmissions,
    isLoading,
    allowHint,
    codeChangedSinceLastSubmit,
    isGeneratingHint,
    hasLastSubmission,
    hasStarterCode
}) {
    const currentUser = useSelector(selectCurrentUser);
    const demoTimeRemaining = currentUser?.exp
        ? Math.max(0, Math.floor((new Date(currentUser.exp * 1000) - new Date()) / 1000 / 60))
        : null;

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
              <div className="relative group inline-block">
                <button
                  onClick={onGetHint}
                  disabled={isLoading || codeChangedSinceLastSubmit}
                  className="py-2 px-4 text-base font-medium text-white bg-success hover:bg-success-hover disabled:bg-ui-light rounded transition-colors"
                >
                  {isGeneratingHint ? "Getting Hint..." : "Get Hint"}
                </button>
		{codeChangedSinceLastSubmit && <div
                  className="
                    pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2
                    whitespace-nowrap rounded bg-gray-800 px-2 py-1 text-white
                    opacity-0 transition-opacity group-hover:opacity-100
                  "
                >
                  Your hint is only valid for your last submission
                </div>}
              </div> : null
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

            {/* Demo mode indicator as a button-like element (temporarily hidden)
                    {isDemo && (
                        <div className="py-2 px-4 text-base font-medium text-ui-dark bg-notice-yellowBg rounded flex items-center">
                            <span className="mr-2">🕒</span>
                            Demo Mode, Time Remaining: {demoTimeRemaining} min
                        </div>
                    )}
                    */}
          </div>

          {/* Right side - Status info */}
          <div className="flex space-x-8">
            {team && (
              <div className="text-lg font-medium">
                <span className="text-ui-light">TEAM:</span> {team}
              </div>
            )}
            {game && (
              <div className="text-lg font-medium">
                <span className="text-ui-light">GAME:</span> {game}
              </div>
            )}
            {league && (
              <div className="text-lg font-medium">
                <span className="text-ui-light">LEAGUE:</span> {league}
              </div>
            )}
          </div>
        </div>
      </div>
    );
}

export default CombinedFooter;
