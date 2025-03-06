import React, { useState } from 'react';
import { getFeedbackComponent } from '../Feedback/utils/FeedbackRegistry';

const FeedbackSelector = ({ feedback }) => {
    // Start expanded by default
    const [isExpanded, setIsExpanded] = useState(true);

    if (!feedback) return null;

    const FeedbackComponent = getFeedbackComponent(feedback);

    return (
        <div className="relative mb-10">
            <div className={`relative ${isExpanded ? 'h-auto' : 'max-h-48 overflow-hidden'}`}>
                <FeedbackComponent feedback={feedback} />
            </div>
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className={`
                  absolute left-0 right-0 h-10 flex items-center justify-center
                  bg-gradient-to-b from-transparent to-ui-dark
                  text-white cursor-pointer w-full hover:bg-opacity-90
                  ${isExpanded ? '-bottom-10' : 'bottom-0'}
                `}
            >
                {isExpanded ? 'Show Less ▲' : 'Show More ▼'}
            </button>
        </div>
    );
};

export default FeedbackSelector;