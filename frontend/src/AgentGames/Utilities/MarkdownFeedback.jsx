import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './css/markdownFeedback.css';

const MarkdownFeedback = ({ feedback }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <div className="markdown-feedback">
      <div
        className="feedback-header"
        onClick={toggleExpand}
      >
        <h3>Feedback (press down arrow to expand)</h3>
        <span className={`expand-icon ${isExpanded ? 'expanded' : ''}`}></span>
      </div>
      <div className={`feedback-content ${isExpanded ? 'expanded' : ''}`}>
        <ReactMarkdown>{feedback}</ReactMarkdown>
      </div>
    </div>
  );
};

export default MarkdownFeedback;