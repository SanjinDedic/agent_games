// MarkdownFeedback.jsx
import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import './css/markdownFeedback.css';

const MarkdownFeedback = ({ feedback }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  const renderContent = () => {
    if (typeof feedback !== 'string') {
      return <div className="feedback-error">Error: Markdown feedback must be a string</div>;
    }
    
    return (
      <ReactMarkdown rehypePlugins={[rehypeRaw]}>
        {feedback}
      </ReactMarkdown>
    );
  };

  return (
    <div className="markdown-feedback">
      <div className="feedback-header" onClick={toggleExpand}>
        <h3>Feedback (press down arrow to expand)</h3>
        <span className={`expand-icon ${isExpanded ? 'expanded' : ''}`}></span>
      </div>
      <div className={`feedback-content ${isExpanded ? 'expanded' : ''}`}>
        {renderContent()}
      </div>
    </div>
  );
};

export default MarkdownFeedback;