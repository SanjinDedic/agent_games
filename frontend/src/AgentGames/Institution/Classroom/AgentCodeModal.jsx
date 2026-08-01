import React, { useState } from 'react';

import usePlagiarismAssessment from '../../Shared/hooks/usePlagiarismAssessment';
import { useTerms } from '../../Shared/terminology';
import CodeHistoryViewer, {
  formatDuration,
} from '../../Shared/Submission/CodeHistoryViewer';
import PlagiarismReportModal from '../../Shared/PlagiarismReportModal';

/**
 * Modal showing one team's full agent submission history: read-only Monaco
 * viewer with prev/next, opened on whichever submission was clicked in the
 * grid. The AI plagiarism assessment acts on the team being read.
 */
function AgentCodeModal({
  teamName,
  teamId,
  leagueId,
  submissions,
  initialIndex,
  onClose,
}) {
  const T = useTerms();
  const [index, setIndex] = useState(initialIndex);
  const { assessing, report, clearReport, assess } = usePlagiarismAssessment();

  return (
    <>
      <div
        className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-6"
        onClick={onClose}
      >
        <div
          className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6 flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex justify-between items-start gap-4 mb-4">
            <h3 className="text-xl font-bold text-ui-dark">
              {teamName} — submissions
            </h3>
            <div className="flex items-center gap-3">
              <button
                onClick={() => assess({ teamId, leagueId, teamName })}
                disabled={assessing}
                className="px-4 py-2 text-sm font-semibold rounded-lg bg-primary text-white hover:bg-primary-hover transition-colors disabled:opacity-50"
              >
                {assessing ? 'Assessing...' : 'AI plagiarism assessment'}
              </button>
              <button
                onClick={onClose}
                className="text-ui hover:text-ui-dark text-2xl leading-none"
                aria-label="Close"
              >
                ×
              </button>
            </div>
          </div>

          {submissions.length === 0 ? (
            <div className="text-ui py-8 text-center">
              {`This ${T.team} has no validated submissions yet.`}
            </div>
          ) : (
            <div className="h-[60vh] flex flex-col">
              <CodeHistoryViewer
                submissions={submissions}
                index={index}
                onIndexChange={setIndex}
                renderMeta={(sub) => (
                  <span className="text-xs text-gray-500">
                    {sub?.ranking != null
                      ? `Validation placement: #${sub.ranking}`
                      : 'Not ranked'}
                    {' · sim '}
                    {formatDuration(sub?.duration_ms)}
                  </span>
                )}
              />
            </div>
          )}
        </div>
      </div>

      <PlagiarismReportModal report={report} onClose={clearReport} />
    </>
  );
}

export default AgentCodeModal;
