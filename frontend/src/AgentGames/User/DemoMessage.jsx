// New component: DemoMessage.jsx
import React from 'react';

const DemoMessage = () => {
    return (
        <div className="mb-6 bg-notice-yellowBg border border-notice-yellow rounded-lg p-4">
            <div className="flex items-center space-x-2">
                <span className="text-lg">🕒</span>
                <p className="text-ui-dark font-medium">
                    DEMO MODE - You are currently using the demo version of Agent Games
                </p>
            </div>
            <p className="text-ui-dark mt-2">
                Your code and submissions will be available for the duration of your demo session.
            </p>
        </div>
    );
};

export default DemoMessage;