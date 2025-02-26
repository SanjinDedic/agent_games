import React from 'react';

function Leaderboards() {
    return (
        <div className="min-h-screen pt-16 flex flex-col items-center bg-ui-lighter">
            <div className="w-full max-w-4xl px-4">
                <div className="bg-white rounded-lg shadow-lg p-8">
                    <h1 className="text-2xl font-bold text-ui-dark mb-4">Global Leaderboards</h1>
                    <p className="text-ui-dark mb-6">View top-performing players across all institutions.</p>
                    {/* Leaderboard content would go here */}
                </div>
            </div>
        </div>
    );
}

export default Leaderboards;