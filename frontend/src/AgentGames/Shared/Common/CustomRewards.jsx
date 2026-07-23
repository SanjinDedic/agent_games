// src/AgentGames/Shared/Common/CustomRewards.jsx
import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useDispatch, useSelector } from 'react-redux';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import { setRewards } from '../../../slices/leaguesSlice';

const markdownComponents = {
  h1: (props) => <h1 className="text-xl font-bold text-ui-dark mt-3 mb-2" {...props} />,
  h2: (props) => <h2 className="text-lg font-semibold text-ui-dark mt-3 mb-2" {...props} />,
  h3: (props) => <h3 className="text-base font-semibold text-ui-dark mt-2 mb-1" {...props} />,
  p: (props) => <p className="text-sm text-ui-dark leading-relaxed mb-2" {...props} />,
  ul: (props) => <ul className="list-disc list-outside pl-5 text-sm text-ui-dark mb-2 space-y-1" {...props} />,
  ol: (props) => <ol className="list-decimal list-outside pl-5 text-sm text-ui-dark mb-2 space-y-1" {...props} />,
  li: (props) => <li className="text-sm text-ui-dark" {...props} />,
  strong: (props) => <strong className="font-semibold text-ui-dark" {...props} />,
  em: (props) => <em className="italic" {...props} />,
  code: ({ inline, className, children, ...props }) => (
    <code
      className="px-1 py-0.5 rounded bg-ui-lighter font-mono text-xs text-ui-dark"
      {...props}
    >
      {children}
    </code>
  ),
  table: (props) => (
    <div className="overflow-x-auto mb-2">
      <table className="min-w-full text-xs border border-ui-light" {...props} />
    </div>
  ),
  thead: (props) => <thead className="bg-ui-lighter" {...props} />,
  th: (props) => <th className="px-2 py-1 text-left font-semibold border border-ui-light" {...props} />,
  td: (props) => <td className="px-2 py-1 border border-ui-light" {...props} />,
};

/**
 * Schema-aware custom rewards input. The shape, length, default values and
 * per-cell labels all come from the selected game's `reward_schema` exposed
 * via `/user/get-game-instructions`. When the schema is null the component
 * renders nothing — the game does not support custom rewards.
 */
const CustomRewards = () => {
  const dispatch = useDispatch();
  const schema = useSelector((state) => state.leagues.currentRewardSchema);
  const instructions = useSelector((state) => state.leagues.currentRewardInstructions);
  const rewards = useSelector((state) => state.leagues.currentRewards);

  const [inputValue, setInputValue] = useState('');
  const [error, setError] = useState('');
  // Collapsed by default: most runs use the default rewards, and the explainer
  // is long. The input stays mounted so a typed value survives collapsing.
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    setInputValue('');
    setError('');
  }, [schema]);

  if (!schema) {
    return null;
  }

  const defaultStr = JSON.stringify(schema.default);

  const handleInputChange = (event) => {
    const value = event.target.value;
    setInputValue(value);

    if (!value.trim().endsWith(']')) {
      dispatch(setRewards(null));
      setError(`Please type the correct format. Example: ${defaultStr}`);
      return;
    }

    try {
      const parsed = JSON.parse(value);
      if (!Array.isArray(parsed) || !parsed.every((item) => typeof item === 'number')) {
        throw new Error('Not a numeric array');
      }
      if (parsed.length !== schema.length) {
        const msg = `${schema.kind === 'matrix' ? 'Payoff matrix' : 'Rewards list'} must have exactly ${schema.length} entries.`;
        dispatch(setRewards(null));
        setError(msg);
        toast.error(msg);
        return;
      }
      dispatch(setRewards(parsed));
      setError('');
    } catch (e) {
      dispatch(setRewards(null));
      const msg = `Invalid input. Enter a numeric JSON array like ${defaultStr}.`;
      setError(msg);
      toast.error(msg);
    }
  };

  const activeSummary = rewards ? JSON.stringify(rewards) : `Default ${defaultStr}`;

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        className="w-full flex flex-wrap items-center justify-between gap-2 text-left"
      >
        <span className="flex flex-wrap items-baseline gap-2">
          <span className="text-xl font-semibold text-ui-dark">Custom Rewards</span>
          <span className="font-mono text-sm text-ui">{activeSummary}</span>
        </span>
        <span className="flex items-center gap-2 text-sm text-primary">
          {isOpen ? 'Hide' : 'Edit'}
          <span
            className={`transform transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          >
            ▼
          </span>
        </span>
      </button>

      <div
        className={`grid grid-cols-1 lg:grid-cols-5 gap-6 mt-4 ${isOpen ? '' : 'hidden'}`}
      >
        {/* Markdown explainer */}
        {instructions && (
          <div className="lg:col-span-3 max-w-none text-ui-dark">
            <ReactMarkdown rehypePlugins={[rehypeRaw]} components={markdownComponents}>
              {instructions}
            </ReactMarkdown>
          </div>
        )}

        {/* Input column */}
        <div className={instructions ? 'lg:col-span-2 space-y-3' : 'lg:col-span-5 space-y-3'}>
          <label className="block text-sm font-medium text-ui-dark">
            Enter rewards as a JSON array
            <input
              type="text"
              value={inputValue}
              onChange={handleInputChange}
              placeholder={defaultStr}
              className="w-full mt-1 p-2 border border-ui-light rounded-lg text-base font-mono"
            />
          </label>

          {schema.kind === 'matrix' && Array.isArray(schema.labels) && schema.labels.length === schema.length && (
            <div className="text-xs text-ui">
              <p className="font-medium mb-1">Index order:</p>
              <ol className="list-decimal list-inside space-y-0.5">
                {schema.labels.map((label, i) => (
                  <li key={i}>
                    <span className="font-mono">[{i}]</span> {label}
                  </li>
                ))}
              </ol>
            </div>
          )}

          {error && <p className="text-sm text-danger">{error}</p>}

          <p className="text-xs text-ui">
            Default: <span className="font-mono">{defaultStr}</span>
            {' '}
            ({schema.length} entries)
          </p>
        </div>
      </div>
    </div>
  );
};

export default CustomRewards;
