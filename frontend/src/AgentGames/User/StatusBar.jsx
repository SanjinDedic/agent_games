// StatusBar.jsx
import React from 'react';

function StatusBar({ team, game, league, isDemo }) {
    return (
        <div className="bg-ui p-4 text-white">
            <div className="grid grid-cols-3 gap-4 text-center">
                {team && (
                    <div className="text-lg font-medium overflow-hidden text-ellipsis whitespace-nowrap">
                        TEAM: {team}
                    </div>
                )}
                {game && (
                    <div className="text-lg font-medium overflow-hidden text-ellipsis whitespace-nowrap">
                        GAME: {game}
                    </div>
                )}
                {league && (
                    <div className="text-lg font-medium overflow-hidden text-ellipsis whitespace-nowrap">
                        LEAGUE: {league}
                    </div>
                )}
            </div>

            {/* Demo Mode Indicator */}
            {isDemo && (
                <div className="mt-2 bg-notice-yellowBg border border-notice-yellow rounded-lg p-2">
                    <div className="flex items-center space-x-2">
                        <span className="text-lg">🕒</span>
                        <p className="text-ui-dark font-medium text-sm">
                            DEMO MODE - Access is temporary
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}

export default StatusBar;