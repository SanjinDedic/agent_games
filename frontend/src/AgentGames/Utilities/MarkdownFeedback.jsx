import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';

const MarkdownFeedback = ({ feedback }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const renderContent = () => {
    if (typeof feedback !== 'string') {
      return <div className="text-danger font-medium">Error: Markdown feedback must be a string</div>;
    }

    return (
      <ReactMarkdown
        rehypePlugins={[rehypeRaw]}
        className="prose prose-sm max-w-none"
      >
        {feedback}
      </ReactMarkdown>
    );
  };

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <div
        className="flex justify-between items-center p-4 bg-ui-lighter cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <h3 className="text-lg font-medium text-ui-dark m-0">
          Feedback (press down arrow to expand)
        </h3>
        <span className={`transform transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}>
          ▼
        </span>
      </div>
      <div className={`
        p-5 bg-white text-ui-dark
        transition-all duration-300
        ${isExpanded ? 'max-h-full' : 'max-h-72 overflow-y-auto'}
      `}>
        {renderContent()}
      </div>
    </div>
  );
};

export default MarkdownFeedback;