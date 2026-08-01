// src/AgentGames/Shared/hooks/usePlagiarismAssessment.js
import { useCallback, useState } from 'react';
import { useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import { selectToken } from '../../../slices/authSlice';
import { authFetch } from '../../../utils/authFetch';
import { useTerms } from '../terminology';

/**
 * Confirm-then-run flow for the AI plagiarism check. Owns the consent
 * dialog (it triggers a paid OpenAI call), the /ai/assess-plagiarism
 * request and the report state; callers render
 * <PlagiarismReportModal report={report} onClose={clearReport} />.
 */
export const usePlagiarismAssessment = () => {
  const T = useTerms();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);
  const [assessing, setAssessing] = useState(false);
  const [report, setReport] = useState(null);

  const clearReport = useCallback(() => setReport(null), []);

  const assess = useCallback(
    async ({ teamId, leagueId, teamName }) => {
      if (!teamId) {
        toast.error(`${T.Team} id not found`);
        return;
      }
      const confirmed = window.confirm(
        `This will send ${teamName}'s code submissions to OpenAI for analysis. Continue?`
      );
      if (!confirmed) return;

      setAssessing(true);
      setReport(null);
      try {
        const response = await authFetch(`${apiUrl}/ai/assess-plagiarism`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({
            league_id: Number(leagueId),
            team_id: Number(teamId),
          }),
        });
        const data = await response.json();
        if (response.ok) {
          setReport(data);
        } else {
          toast.error(data.detail || 'Assessment failed');
        }
      } catch (e) {
        console.error('Error running plagiarism assessment:', e);
        toast.error('Network error running assessment');
      } finally {
        setAssessing(false);
      }
    },
    [apiUrl, accessToken, T]
  );

  return { assessing, report, clearReport, assess };
};

export default usePlagiarismAssessment;
