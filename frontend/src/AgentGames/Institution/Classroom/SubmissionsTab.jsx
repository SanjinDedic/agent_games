import React, { useEffect, useMemo, useState } from 'react';
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
 * All agent submissions for the classroom: team picker on the right, a
 * read-only Monaco history viewer on the left, and the on-demand plagiarism
 * assessment. (Formerly the standalone InstitutionLeagueSubmissions page.)
 */
function SubmissionsTab({ league }) {
  const T = useTerms();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);

  // submissions: { teamName: [{ code, timestamp, id, duration_ms }, ...] }
  const [submissions, setSubmissions] = useState({});
  const [teamIds, setTeamIds] = useState({});
  const [selectedTeam, setSelectedTeam] = useState('');
  const [submissionIndex, setSubmissionIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [assessing, setAssessing] = useState(false);
  const [report, setReport] = useState(null);

  const teamList = useMemo(
    () => Object.keys(submissions).sort((a, b) => a.localeCompare(b)),
    [submissions]
  );

  const teamSubmissions = submissions[selectedTeam] || [];

  useEffect(() => {
    const fetchSubmissions = async () => {
      if (!league.id || !accessToken) return;
      try {
        setLoading(true);
        setError('');
        const resp = await authFetch(
          `${apiUrl}/user/get-all-league-submissions/${league.id}`,
          { headers: { Authorization: `Bearer ${accessToken}` } }
        );
        const data = await resp.json();
        if (resp.ok) {
          const map = data.teams || {};
          setSubmissions(map);
          setTeamIds(data.team_ids || {});
          const firstTeam = Object.keys(map).sort()[0] || '';
          setSelectedTeam(firstTeam);
          // Start at latest submission
          const subs = map[firstTeam] || [];
          setSubmissionIndex(subs.length > 0 ? subs.length - 1 : 0);
        } else {
          setError(data.detail || 'Failed to load submissions');
        }
      } catch (e) {
        setError('Error fetching submissions');
      } finally {
        setLoading(false);
      }
    };
    fetchSubmissions();
  }, [apiUrl, accessToken, league.id]);

  const handleSelectTeam = (team) => {
    setSelectedTeam(team);
    const subs = submissions[team] || [];
    setSubmissionIndex(subs.length > 0 ? subs.length - 1 : 0);
  };

  const handleAssessPlagiarism = async () => {
    if (!selectedTeam || !league.id) return;
    const teamId = teamIds[selectedTeam];
    if (!teamId) {
      toast.error(`${T.Team} id not found`);
      return;
    }
    const proceed = window.confirm(
      `This will send ${selectedTeam}'s code submissions to OpenAI for analysis. Continue?`
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
          league_id: Number(league.id),
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

  if (loading) {
    return <div className="p-6 bg-white rounded-lg shadow">Loading submissions…</div>;
  }
  if (error) {
    return <div className="p-6 bg-white rounded-lg shadow text-danger">{error}</div>;
  }
  if (teamList.length === 0) {
    return (
      <div className="p-6 bg-white rounded-lg shadow">
        {`No submissions found for this ${T.league}.`}
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-col lg:flex-row gap-4 h-[75vh]">
        {/* Left: Monaco Editor + navigation */}
        <CodeHistoryViewer
          submissions={teamSubmissions}
          index={submissionIndex}
          onIndexChange={setSubmissionIndex}
        />

        {/* Right: Team list */}
        <div className="w-full lg:w-1/2 bg-white rounded-lg shadow p-4 overflow-y-auto">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-ui-dark">{T.Teams}</h2>
            {selectedTeam && (
              <button
                onClick={handleAssessPlagiarism}
                disabled={assessing}
                className="px-3 py-1 text-sm rounded bg-primary text-white hover:bg-primary-hover transition-colors disabled:opacity-50"
              >
                {assessing ? 'Assessing...' : `Assess ${selectedTeam}`}
              </button>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {teamList.map((team) => {
              const subs = submissions[team] || [];
              const latestDuration =
                subs.length > 0 ? subs[subs.length - 1].duration_ms : null;
              return (
                <button
                  key={team}
                  onClick={() => handleSelectTeam(team)}
                  className={`text-left px-3 py-2 rounded border transition-colors text-sm ${
                    team === selectedTeam
                      ? 'bg-primary text-white border-primary'
                      : 'bg-ui-lighter text-ui-dark border-ui-light hover:bg-ui-light'
                  }`}
                  title="View submissions"
                >
                  <div className="font-medium truncate">{team}</div>
                  <div className="text-xs opacity-75">
                    {subs.length} submission{subs.length !== 1 ? 's' : ''}
                  </div>
                  {subs.length > 0 && (
                    <div className="text-xs opacity-75">
                      Latest sim: {formatDuration(latestDuration)}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <PlagiarismReportModal report={report} onClose={() => setReport(null)} />
    </>
  );
}

export default SubmissionsTab;
