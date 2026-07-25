import React, { useState } from 'react';
import { useSelector } from 'react-redux';
import { toast } from 'react-toastify';

import { selectToken } from '../../../slices/authSlice';
import { authFetch } from '../../../utils/authFetch';
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
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);

  const [index, setIndex] = useState(initialIndex);
  const [assessing, setAssessing] = useState(false);
  const [report, setReport] = useState(null);

  const handleAssessPlagiarism = async () => {
    if (!teamId) {
      toast.error(`${T.Team} id not found`);
      return;
    }
    const proceed = window.confirm(
      `This will send ${teamName}'s code submissions to OpenAI for analysis. Continue?`
    );
    if (!proceed) return;

    setAssessing(true);
    setReport(null);
    try {
      const resp = await authFetch(`${apiUrl}/ai/assess-plagiarism`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          league_id: Number(leagueId),
          team_id: teamId,
        }),
      });
      const data = await resp.json();
      if (resp.ok) {
        setReport(data);
      } else {
        toast.error(data.detail || 'Assessment failed');
      }
    } catch (e) {
      toast.error('Network error running assessment');
    } finally {
      setAssessing(false);
    }
  };

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
                onClick={handleAssessPlagiarism}
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

      <PlagiarismReportModal report={report} onClose={() => setReport(null)} />
    </>
  );
}

export default AgentCodeModal;
