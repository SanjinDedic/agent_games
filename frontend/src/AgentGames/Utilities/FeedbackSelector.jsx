import React, { useState } from 'react';
import MarkdownFeedback from './MarkdownFeedback';
import JsonFeedback from './JsonFeedback';
import PrisonersFeedback from './PrisonersFeedback';

const FeedbackSelector = ({ feedback }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!feedback) return null;

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  const feedbackContainerStyle = {
    position: 'relative',
    maxHeight: isExpanded ? 'none' : '200px',
    overflow: 'hidden',
    transition: 'max-height 0.3s ease-out',
  };

  const expandButtonStyle = {
    position: 'absolute',
    bottom: isExpanded ? '-40px' : '0',
    left: '0',
    right: '0',
    height: '40px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(to bottom, transparent, #333)',
    color: 'white',
    cursor: 'pointer',
    border: 'none',
    width: '100%',
  };

  const containerStyle = {
    position: 'relative',
    marginBottom: isExpanded ? '40px' : '0',
  };

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
      <div className="feedback-error">
        Error: Feedback must be either a string for markdown or an object for JSON
      </div>
    );
  };

  return (
    <div style={containerStyle}>
      <div style={feedbackContainerStyle}>
        {renderFeedback()}
      </div>
      <button 
        onClick={toggleExpand} 
        style={expandButtonStyle}
        className="hover:bg-opacity-90"
      >
        {isExpanded ? 'Show Less ▲' : 'Show More ▼'}
      </button>
    </div>
  );
};

export default FeedbackSelector;