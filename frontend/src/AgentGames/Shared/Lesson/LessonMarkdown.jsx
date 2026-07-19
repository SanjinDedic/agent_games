import React from 'react';
import ReactMarkdown, { defaultUrlTransform } from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import RunnableCodeBlock from './RunnableCodeBlock';
import { useLessonModal } from './LessonModalContext';

const LESSON_LINK_PREFIX = 'lesson://';

// react-markdown's default transform strips unknown URL protocols for
// safety, which would blank lesson:// hrefs before the `a` override runs —
// let those through untouched, sanitize everything else as usual.
const urlTransform = (url) =>
  url.startsWith(LESSON_LINK_PREFIX) ? url : defaultUrlTransform(url);

// Uses its own .lesson-markdown class (not .markdown-content) so pages that
// also mount PureMarkdown — whose .markdown-content rules add full-page
// margins and `all: initial` — can't restyle lesson content.
const markdownStyles = `
  .lesson-markdown {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
    line-height: 1.6;
    color: #333;
    width: 100%;
    padding: 0;
  }
  .lesson-markdown h1, .lesson-markdown h2, .lesson-markdown h3, .lesson-markdown h4, .lesson-markdown h5, .lesson-markdown h6 {
    margin-top: 12px;
    margin-bottom: 4px;
    font-weight: 600;
    line-height: 1.25;
  }
  .lesson-markdown h1 {
    font-size: 1.8em;
    border-bottom: 1px solid #eaecef;
    padding-bottom: 0.2em;
  }
  .lesson-markdown h2 {
    font-size: 1.3em;
    border-bottom: 1px solid #eaecef;
    padding-bottom: 0.1em;
  }
  .lesson-markdown h3 {
    font-size: 1.25em;
  }
  .lesson-markdown p, .lesson-markdown ul, .lesson-markdown ol {
    margin-top: 0;
    margin-bottom: 16px;
  }
  .lesson-markdown ul, .lesson-markdown ol {
    padding-left: 24px;
  }
  .lesson-markdown ul { list-style: disc; }
  .lesson-markdown ol { list-style: decimal; }
  .lesson-markdown code {
    padding: 0.2em 0.4em;
    margin: 0;
    font-size: 100%;
    background-color: rgba(27,31,35,0.05);
    border-radius: 3px;
  }
  .lesson-markdown pre:not(.not-prose *) {
    padding: 16px;
    overflow: auto;
    font-size: 100%;
    line-height: 1.45;
    background-color: #f6f8fa;
    border-radius: 3px;
    margin-bottom: 16px;
  }
  .lesson-markdown pre code {
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

// An ```output-mark block is a graded ```python-run: a `--- expected ---`
// line (however spaced) splits the fence into the starter code shown in the
// editor (above) and the target output the run is checked against (below).
// The separator lives in the fence *content* — not the info-string meta —
// because rehypeRaw round-trips the tree through HTML and drops node.data.meta.
// Without a separator the whole block is just runnable code with no target.
const EXPECTED_SEPARATOR = /^\s*-{3,}\s*expected\s*-{3,}\s*$/i;

const parseOutputMark = (text) => {
  const lines = text.split('\n');
  const sep = lines.findIndex((line) => EXPECTED_SEPARATOR.test(line));
  if (sep === -1) return { code: text, expected: null };
  return {
    code: lines.slice(0, sep).join('\n').replace(/\s+$/, ''),
    expected: lines.slice(sep + 1).join('\n'),
  };
};

/**
 * The lesson-aware markdown renderer, used for lesson content, exercise
 * problem markdown, and tutorial descriptions:
 *
 * - `[text](lesson://my-slug)` links open the lesson modal instead of
 *   navigating.
 * - ```python-run fences render as editable RunnableCodeBlocks.
 * - ```output-mark fences are graded RunnableCodeBlocks: a `--- expected ---`
 *   line marks the target output, and a matching run earns a green tick.
 * - Other fenced languages get Prism syntax highlighting.
 */
function LessonMarkdown({ content }) {
  const { openLesson } = useLessonModal();

  const components = {
    a({ node, href, children, ...props }) {
      if (href?.startsWith(LESSON_LINK_PREFIX)) {
        const slug = href.slice(LESSON_LINK_PREFIX.length);
        return (
          <button
            type="button"
            onClick={() => openLesson(slug)}
            className="text-primary underline hover:text-primary-hover font-medium cursor-pointer bg-transparent border-0 p-0"
          >
            {children}
          </button>
        );
      }
      return (
        <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
          {children}
        </a>
      );
    },
    // Fenced blocks with a language bring their own container (Monaco or
    // SyntaxHighlighter), so unwrap the surrounding <pre> for those; plain
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
      if (match && match[1] === 'python-run') {
        return <RunnableCodeBlock initialCode={text} />;
      }
      if (match && match[1] === 'output-mark') {
        const { code, expected } = parseOutputMark(text);
        return (
          <RunnableCodeBlock initialCode={code} expectedOutput={expected} />
        );
      }
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
  };

  return (
    <>
      <style>{markdownStyles}</style>
      <div className="lesson-markdown">
        <ReactMarkdown
          components={components}
          rehypePlugins={[rehypeRaw]}
          urlTransform={urlTransform}
        >
          {content}
        </ReactMarkdown>
      </div>
    </>
  );
}

export default LessonMarkdown;
