import React from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'; // Import the vscDarkPlus theme.

const PureMarkdown = ({ content }) => {
  const markdownStyles = `
    .markdown-content {
      all: initial;
      *:not(video) {
        all: revert;
      }
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
      line-height: 1.6;
      color: #333;
      max-width: 800px;
      margin: 0 auto;
      margin-top: 60px;
      padding: 20px;
    }
    .markdown-content h1, .markdown-content h2, .markdown-content h3, .markdown-content h4, .markdown-content h5, .markdown-content h6 {
      margin-top: 24px;
      margin-bottom: 16px;
      font-weight: 600;
      line-height: 1.25;
    }
    .markdown-content h1 {
      font-size: 2em;
      border-bottom: 1px solid #eaecef;
      padding-bottom: 0.3em;
    }
    .markdown-content h2 {
      font-size: 1.5em;
      border-bottom: 1px solid #eaecef;
      padding-bottom: 0.3em;
    }
    .markdown-content h3 {
      font-size: 1.25em;
    }
    .markdown-content p, .markdown-content ul, .markdown-content ol {
      margin-top: 0;
      margin-bottom: 16px;
    }
    .markdown-content code {
      padding: 0.2em 0.4em;
      margin: 0;
      font-size: 100%; 
      background-color: rgba(27,31,35,0.05);
      border-radius: 3px;
    }
    .markdown-content pre {
      padding: 16px;
      overflow: auto;
      font-size: 100%; 
      line-height: 1.45;
      background-color: #f6f8fa;
      border-radius: 3px;
    }
    .markdown-content pre code {
      font-size: 16px !important;
      line-height: 1.6 !important;
      display: inline;
      max-width: auto;
      padding: 0;
      margin: 0;
      overflow: visible;
      line-height: inherit;
      word-wrap: normal;
      background-color: transparent;
      border: 0; 
    }
  `;

  // Render custom code blocks using react-syntax-highlighter
  const components = {
    code({ node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '');
      return !inline && match ? (
        <SyntaxHighlighter
          style={vscDarkPlus} // Use vscDarkPlus theme for highlighting
          language={match[1]}
          PreTag="div"
          {...props}

        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      ) : (
        <code className={className} {...props}>
          {children}
        </code>
      );
    }
  };

  return (
    <>
      <style>{markdownStyles}</style>
      <div className="markdown-content">
        <ReactMarkdown components={components} rehypePlugins={[rehypeRaw]}>
          {content}
        </ReactMarkdown>
      </div>
    </>
  );
};

export default PureMarkdown;