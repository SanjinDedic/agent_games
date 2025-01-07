import React, { useState } from 'react';
import MarkdownFeedback from './MarkdownFeedback';
import JsonFeedback from './JsonFeedback';
import PrisonersFeedback from './PrisonersFeedback';

const FeedbackSelector = ({ feedback }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!feedback) return null;

  const renderFeedback = () => {
    if (typeof feedback === 'string') {
      return <MarkdownFeedback feedback={feedback} />;
    }

    if (typeof feedback === 'object' && feedback !== null && !Array.isArray(feedback)) {
      if (feedback.game === 'prisoners_dilemma') {
        return <PrisonersFeedback feedback={feedback} />;
      }
      return <JsonFeedback feedback={feedback} />;
    }

    return (
      <div className="text-danger font-medium">
        Error: Feedback must be either a string for markdown or an object for JSON
      </div>
    );
  };

  return (
    <div className="relative mb-10">
      <div className={`relative ${isExpanded ? 'h-auto' : 'max-h-48 overflow-hidden'}`}>
        {renderFeedback()}
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