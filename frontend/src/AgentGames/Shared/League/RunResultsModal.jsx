// src/AgentGames/Shared/League/RunResultsModal.jsx
import React, { useState } from 'react';
import moment from 'moment-timezone';

import ResultsDisplay from '../Utilities/ResultsDisplay';
import FeedbackSelector from '../../Feedback/FeedbackSelector';
import { useTerms } from '../terminology';

/**
 * Full results of one simulation run in a modal: the leaderboard table and,
 * when the run carries it, the feedback students see. Lives out of the page
 * flow so the simulation tab stays short and the table is revealed on demand
 * — teachers often project this reveal to their class.
 */
const RunResultsModal = ({ simulation, onClose }) => {
  const T = useTerms();
  const hasFeedback = Boolean(simulation?.feedback);
  const [tab, setTab] = useState('leaderboard');

  const tabs = [
    { key: 'leaderboard', label: 'Leaderboard' },
    ...(hasFeedback
      ? [{ key: 'feedback', label: `${T.Team} feedback` }]
      : []),
  ];

  return (
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-6"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-xl font-bold text-ui-dark">Run results</h3>
            <div className="text-sm text-ui mt-0.5">
              {moment(simulation.timestamp).format('D MMM YYYY, h:mm a')} ·{' '}
              {(simulation.num_simulations || 0).toLocaleString()} games
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-ui hover:text-ui-dark text-2xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {tabs.length > 1 && (
          <div className="flex gap-1 border-b border-ui-light mb-4">
            {tabs.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`px-4 py-2 text-base font-medium rounded-t-lg transition-colors ${
                  tab === key
                    ? 'bg-white text-primary border border-b-0 border-ui-light'
                    : 'text-ui hover:text-ui-dark hover:bg-ui-lighter'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        )}

        {tab === 'feedback' && hasFeedback ? (
          <FeedbackSelector feedback={simulation.feedback} collapsible={false} />
        ) : (
          <ResultsDisplay
            data={simulation}
            highlight={false}
            data_message={simulation.message}
            tablevisible={true}
          />
        )}
      </div>
    </div>
  );
};

export default RunResultsModal;
