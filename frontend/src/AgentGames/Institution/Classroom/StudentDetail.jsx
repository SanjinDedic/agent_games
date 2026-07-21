import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { toast } from 'react-toastify';
import moment from 'moment-timezone';

import { authFetch } from '../../../utils/authFetch';
import { selectToken } from '../../../slices/authSlice';
import useClassroomAPI from '../../Shared/hooks/useClassroomAPI';
import { useTerms } from '../../Shared/terminology';
import RankingSparkline from '../../Shared/Progress/RankingSparkline';
import StatusCell from '../../Shared/Progress/StatusCell';
import CodeHistoryViewer from '../../Shared/Submission/CodeHistoryViewer';
import PlagiarismReportModal from '../../Shared/PlagiarismReportModal';
import ExerciseCodeModal from './ExerciseCodeModal';

const Stat = ({ label, children, title }) => (
  <div title={title}>
    <span className="block text-sm text-ui">{label}</span>
    <span className="block text-lg font-medium text-ui-dark">{children}</span>
  </div>
);

/**
 * One student's drill-down: identity + lifetime stats, their full agent
 * submission history in a code viewer (with on-demand plagiarism check),
 * and per-exercise tutorial status with click-through to exercise code.
 */
function StudentDetail() {
  const T = useTerms();
  const { leagueId, teamId } = useParams();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);
  const { getStudentSummary, getStudentAgentSubmissions } = useClassroomAPI();

  const [summary, setSummary] = useState(null);
  const [agentSubmissions, setAgentSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [submissionIndex, setSubmissionIndex] = useState(0);
  const [assessing, setAssessing] = useState(false);
  const [report, setReport] = useState(null);
  // exerciseId while the exercise code modal is open
  const [modalExerciseId, setModalExerciseId] = useState(null);

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      const [summaryResult, submissionsResult] = await Promise.all([
        getStudentSummary(teamId),
        getStudentAgentSubmissions(teamId),
      ]);
      if (!active) return;
      if (summaryResult.success && submissionsResult.success) {
        setSummary(summaryResult.data);
        const subs = submissionsResult.data.submissions || [];
        setAgentSubmissions(subs);
        setSubmissionIndex(subs.length > 0 ? subs.length - 1 : 0);
        setError('');
      } else {
        setError(summaryResult.error || submissionsResult.error);
      }
      setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [getStudentSummary, getStudentAgentSubmissions, teamId]);

  const handleAssessPlagiarism = async () => {
    const team = summary?.team;
    if (!team?.league_id) return;
    const proceed = window.confirm(
      `This will send ${team.name}'s code submissions to OpenAI for analysis. Continue?`
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
          league_id: team.league_id,
          team_id: team.id,
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
    return (
      <div className="min-h-screen bg-ui-lighter pt-20 px-6">
        <div className="max-w-[1400px] mx-auto bg-white rounded-lg shadow-lg p-6 text-ui">
          {`Loading ${T.team}…`}
        </div>
      </div>
    );
  }
  if (error || !summary) {
    return (
      <div className="min-h-screen bg-ui-lighter pt-20 px-6">
        <div className="max-w-[1400px] mx-auto bg-white rounded-lg shadow-lg p-6 text-danger">
          {error || `Failed to load ${T.team}`}
        </div>
      </div>
    );
  }

  const { team, agent, tutorials } = summary;

  return (
    <div className="min-h-screen bg-ui-lighter pt-20 px-6 pb-8">
      <div className="max-w-[1400px] mx-auto space-y-6">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <Link
            to={`/Classroom/${leagueId}/students`}
            className="text-sm text-primary hover:underline"
          >
            ← {`Back to ${team.league_name || T.league}`}
          </Link>
          <div className="flex flex-wrap items-baseline gap-3 mt-1 mb-4">
            <h1 className="text-2xl font-bold text-ui-dark">{team.name}</h1>
            {team.school && <span className="text-ui">{team.school}</span>}
            {agent.achieved_first && (
              <span
                className="text-success font-bold"
                title={`This ${T.team} has reached 1st place`}
              >
                ✓ 1st place
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <Stat label="Agent attempts">{agent.total_attempts}</Stat>
            <Stat label="Validated">{agent.validated_submissions}</Stat>
            <Stat label="Hints used">{agent.hints_used}</Stat>
            <Stat label="Joined">
              {team.created_at ? moment(team.created_at).format('D MMM YYYY') : '—'}
            </Stat>
            <Stat
              label="Last active"
              title={
                summary.last_active
                  ? new Date(summary.last_active).toLocaleString()
                  : undefined
              }
            >
              {summary.last_active ? moment(summary.last_active).fromNow() : '—'}
            </Stat>
            <Stat label="Ranking trend" title="Validation placements, oldest to newest">
              <RankingSparkline history={agent.ranking_history} />
            </Stat>
          </div>
        </div>

        {/* Agent submissions */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex flex-wrap justify-between items-center gap-2 mb-4">
            <h2 className="text-xl font-semibold text-ui-dark">
              Agent Submissions
            </h2>
            {agentSubmissions.length > 0 && (
              <button
                onClick={handleAssessPlagiarism}
                disabled={assessing}
                className="px-3 py-1 text-sm rounded bg-primary text-white hover:bg-primary-hover transition-colors disabled:opacity-50"
              >
                {assessing ? 'Assessing...' : 'Assess plagiarism'}
              </button>
            )}
          </div>
          {agentSubmissions.length === 0 ? (
            <p className="text-ui">{`No validated agent submissions from this ${T.team} yet.`}</p>
          ) : (
            <div className="h-[55vh] flex flex-col">
              <CodeHistoryViewer
                submissions={agentSubmissions}
                index={submissionIndex}
                onIndexChange={setSubmissionIndex}
                renderMeta={(sub) => (
                  <span className="text-xs text-gray-500">
                    {sub?.ranking != null
                      ? `Validation placement: #${sub.ranking}`
                      : 'Not ranked'}
                  </span>
                )}
              />
            </div>
          )}
        </div>

        {/* Tutorial progress */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold text-ui-dark mb-1">
            Tutorial Progress
          </h2>
          <p className="text-sm text-ui mb-4">
            <span className="text-green-700 font-bold">✓</span> passed ·{' '}
            <span className="text-amber-700 font-bold">n</span> attempts without a
            pass · <span className="font-bold">·</span> untouched — click an
            exercise to read the code.
          </p>
          {tutorials.length === 0 ? (
            <p className="text-ui">
              {`No tutorials are attached to this ${T.team}'s ${T.league}.`}
            </p>
          ) : (
            <div className="space-y-5">
              {tutorials.map((tutorial) => (
                <div key={tutorial.id}>
                  <h3 className="text-lg font-medium text-ui-dark mb-2">
                    {tutorial.title}
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {tutorial.exercises.map((exercise) => (
                      <div
                        key={exercise.id}
                        className="flex items-center gap-1.5 border border-ui-light rounded-lg px-2 py-1"
                      >
                        <span className="text-xs text-ui font-mono">
                          {exercise.order_index + 1}
                        </span>
                        <StatusCell
                          status={exercise.status}
                          attempts={exercise.attempts}
                          title={
                            exercise.status === 'untouched'
                              ? `${exercise.title}: not attempted`
                              : `${exercise.title}: ${
                                  exercise.status === 'passed' ? 'passed' : 'not passed'
                                } after ${exercise.attempts} attempt${
                                  exercise.attempts !== 1 ? 's' : ''
                                } (click to view code)`
                          }
                          onClick={() => setModalExerciseId(exercise.id)}
                        />
                        <span className="text-sm text-ui-dark">{exercise.title}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <PlagiarismReportModal report={report} onClose={() => setReport(null)} />

      {modalExerciseId && (
        <ExerciseCodeModal
          teamId={team.id}
          teamName={team.name}
          exerciseId={modalExerciseId}
          onClose={() => setModalExerciseId(null)}
        />
      )}
    </div>
  );
}

export default StudentDetail;
