import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

// Uses its own .rich-markdown class (not .markdown-content) so pages that
// also mount PureMarkdown — whose .markdown-content rules add full-page
// margins and `all: initial` — can't restyle this content.
const markdownStyles = `
  .rich-markdown {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
    line-height: 1.6;
    color: #333;
    width: 100%;
    padding: 0;
  }
  .rich-markdown h1, .rich-markdown h2, .rich-markdown h3, .rich-markdown h4, .rich-markdown h5, .rich-markdown h6 {
    margin-top: 12px;
    margin-bottom: 4px;
    font-weight: 600;
    line-height: 1.25;
  }
  .rich-markdown h1 {
    font-size: 1.8em;
    border-bottom: 1px solid #eaecef;
    padding-bottom: 0.2em;
  }
  .rich-markdown h2 {
    font-size: 1.3em;
    border-bottom: 1px solid #eaecef;
    padding-bottom: 0.1em;
  }
  .rich-markdown h3 {
    font-size: 1.25em;
  }
  .rich-markdown p, .rich-markdown ul, .rich-markdown ol {
    margin-top: 0;
    margin-bottom: 16px;
  }
  .rich-markdown ul, .rich-markdown ol {
    padding-left: 24px;
  }
  .rich-markdown ul { list-style: disc; }
  .rich-markdown ol { list-style: decimal; }
  .rich-markdown code {
    padding: 0.2em 0.4em;
    margin: 0;
    font-size: 100%;
    background-color: rgba(27,31,35,0.05);
    border-radius: 3px;
  }
  .rich-markdown pre:not(.not-prose *) {
    padding: 16px;
    overflow: auto;
    font-size: 100%;
    line-height: 1.45;
    background-color: #f6f8fa;
    border-radius: 3px;
    margin-bottom: 16px;
  }
  .rich-markdown pre code {
    font-size: 13px !important;
    display: inline;
    max-width: auto;
    padding: 0;
    margin: 0;
    overflow: visible;
    line-height: 1.45;
    word-wrap: normal;
    background-color: transparent;
    border: 0;
  }
`;

const codeClassName = (node) => {
  const className = node?.children?.[0]?.properties?.className;
  if (Array.isArray(className)) return className.join(' ');
  return className ? String(className) : '';
};

/**
 * Markdown renderer for game instructions: fenced blocks with a language get
 * Prism syntax highlighting, everything else renders as plain markdown.
 */
function RichMarkdown({ content }) {
  const components = useMemo(() => ({
    // Fenced blocks with a language bring their own container
    // (SyntaxHighlighter), so unwrap the surrounding <pre> for those; plain
    // fences keep the default grey pre box.
    pre({ node, children, ...props }) {
      if (/language-[\w-]+/.test(codeClassName(node))) {
        return <>{children}</>;
      }
      return <pre {...props}>{children}</pre>;
    },
    code({ node, className, children, ...props }) {
      const match = /language-([\w-]+)/.exec(className || '');
      const text = String(children).replace(/\n$/, '');
      if (match) {
        return (
          <SyntaxHighlighter
            style={vscDarkPlus}
            language={match[1]}
            PreTag="div"
            {...props}
          >
            {text}
          </SyntaxHighlighter>
        );
      }
      return (
        <code className={className} {...props}>
          {children}
        </code>
      );
    },
  }), []);

  return (
    <>
      <style>{markdownStyles}</style>
      <div className="rich-markdown">
        <ReactMarkdown components={components} rehypePlugins={[rehypeRaw]}>
          {content}
        </ReactMarkdown>
      </div>
    </>
  );
}

// Memoised because re-parsing the markdown (react-markdown + rehypeRaw's
// hast->HTML->hast round-trip + Prism) is expensive, and the pages that render
// instructions re-render for reasons unrelated to their content.
export default React.memo(RichMarkdown);
