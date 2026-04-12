// src/AgentGames/Institution/InstitutionLeagueSubmissions.jsx
import React, { useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, useParams } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { toast } from "react-toastify";
import { checkTokenExpiry } from "../../slices/authSlice";
import { authFetch } from "../../utils/authFetch";

const verdictColor = (verdict) => {
  switch (verdict) {
    case "organic":
    case "unlikely":
    case "low":
    case "none":
      return "text-green-600";
    case "suspicious":
    case "possible":
    case "medium":
    case "probable_plagiarism":
      return "text-yellow-600";
    case "clearly_copied":
    case "likely":
    case "highly_likely":
    case "high":
    case "likely_plagiarism":
      return "text-red-600";
    case "not_applicable":
      return "text-gray-500";
    default:
      return "text-ui-dark";
  }
};

const formatDeterministicLabel = (level) => {
  if (level === "likely_plagiarism") return "most likely plagiarising";
  if (level === "probable_plagiarism") return "probably plagiarising";
  return "normal typing speed";
};

function InstitutionLeagueSubmissions() {
  const { leagueId } = useParams();
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector((state) => state.auth.token);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);
  const currentUser = useSelector((state) => state.auth.currentUser);

  // submissions: { teamName: [{ code, timestamp, id }, ...] }
  const [submissions, setSubmissions] = useState({});
  const [leagueName, setLeagueName] = useState("");
  const [selectedTeam, setSelectedTeam] = useState("");
  const [submissionIndex, setSubmissionIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [assessing, setAssessing] = useState(false);
  const [report, setReport] = useState(null);

  const teamList = useMemo(() => {
    return Object.keys(submissions).sort((a, b) => a.localeCompare(b));
  }, [submissions]);

  const teamSubmissions = submissions[selectedTeam] || [];
  const currentSubmission = teamSubmissions[submissionIndex];
  const selectedCode = currentSubmission?.code || "";
  const totalSubmissions = teamSubmissions.length;

  // Guard: require institution role (mount-only to avoid loop on logout)
  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (!isAuthenticated || tokenExpired || currentUser.role !== "institution") {
      navigate("/Institution");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch all submissions for league
  useEffect(() => {
    const fetchSubmissions = async () => {
      if (!leagueId || !accessToken) return;
      try {
        setLoading(true);
        setError("");
        const resp = await authFetch(`${apiUrl}/user/get-all-league-submissions/${leagueId}`, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        });
        const data = await resp.json();
        if (data.status === "success") {
          const map = data.data?.teams || {};
          setLeagueName(data.data?.league_name || "");
          setSubmissions(map);
          const firstTeam = Object.keys(map).sort()[0] || "";
          setSelectedTeam(firstTeam);
          // Start at latest submission
          const subs = map[firstTeam] || [];
          setSubmissionIndex(subs.length > 0 ? subs.length - 1 : 0);
        } else if (data.detail === "Invalid token") {
          navigate("/Institution");
        } else {
          setError(data.message || "Failed to load submissions");
        }
      } catch (e) {
        setError("Error fetching submissions");
      } finally {
        setLoading(false);
      }
    };
    fetchSubmissions();
  }, [apiUrl, accessToken, leagueId, navigate]);

  const handleSelectTeam = (team) => {
    setSelectedTeam(team);
    const subs = submissions[team] || [];
    setSubmissionIndex(subs.length > 0 ? subs.length - 1 : 0);
  };

  const handlePrev = () => {
    if (submissionIndex > 0) setSubmissionIndex(submissionIndex - 1);
  };

  const handleNext = () => {
    if (submissionIndex < totalSubmissions - 1) setSubmissionIndex(submissionIndex + 1);
  };

  const handleAssessPlagiarism = async () => {
    if (!selectedTeam || !leagueId) return;
    const proceed = window.confirm(
      `This will send ${selectedTeam}'s code submissions to OpenAI for analysis. Continue?`
    );
    if (!proceed) return;

    setAssessing(true);
    setReport(null);
    try {
      const resp = await authFetch(`${apiUrl}/ai/assess-plagiarism`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          league_id: Number(leagueId),
          team_name: selectedTeam,
        }),
      });
      const data = await resp.json();
      if (data.status === "success") {
        setReport(data.data);
      } else {
        toast.error(data.message || "Assessment failed");
      }
    } catch (e) {
      toast.error("Network error running assessment");
    } finally {
      setAssessing(false);
    }
  };

  const formatTimestamp = (ts) => {
    if (!ts) return "";
    const d = new Date(ts);
    return d.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  return (
    <div className="min-h-screen bg-ui-lighter">
      <div className="max-w-[1800px] mx-auto px-6 pt-20 pb-8">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-ui-dark">
            League Submissions{leagueName ? `: ${leagueName}` : ""}
          </h1>
          <div className="flex items-center gap-2 text-ui">
            <span className="text-sm">League ID:</span>
            <span className="text-sm font-mono px-2 py-1 bg-white rounded border border-ui-light">
              {leagueId}
            </span>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="p-6 bg-white rounded-lg shadow">Loading submissions…</div>
        ) : error ? (
          <div className="p-6 bg-white rounded-lg shadow text-danger">{error}</div>
        ) : teamList.length === 0 ? (
          <div className="p-6 bg-white rounded-lg shadow">No submissions found for this league.</div>
        ) : (
          <div className="flex flex-col lg:flex-row gap-4 h-[80vh]">
            {/* Left: Monaco Editor + navigation */}
            <div className="flex-1 bg-white rounded-lg shadow overflow-hidden flex flex-col">
              <div className="flex-1 min-h-0">
                <Editor
                  height="100%"
                  defaultLanguage="python"
                  theme="vs-dark"
                  value={selectedCode}
                  options={{
                    readOnly: true,
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    wordWrap: "on",
                  }}
                />
              </div>

              {/* Submission navigation bar */}
              {totalSubmissions > 0 && (
                <div className="flex items-center justify-between px-4 py-2 bg-gray-100 border-t border-ui-light">
                  <button
                    onClick={handlePrev}
                    disabled={submissionIndex === 0}
                    className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                      submissionIndex === 0
                        ? "text-gray-400 cursor-not-allowed"
                        : "text-primary hover:bg-primary hover:text-white"
                    }`}
                  >
                    ← Prev
                  </button>

                  <div className="flex flex-col items-center">
                    <span className="text-xs text-ui font-medium">
                      Submission {submissionIndex + 1} of {totalSubmissions}
                    </span>
                    <span className="text-xs text-gray-500">
                      {formatTimestamp(currentSubmission?.timestamp)}
                    </span>
                  </div>

                  <button
                    onClick={handleNext}
                    disabled={submissionIndex === totalSubmissions - 1}
                    className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                      submissionIndex === totalSubmissions - 1
                        ? "text-gray-400 cursor-not-allowed"
                        : "text-primary hover:bg-primary hover:text-white"
                    }`}
                  >
                    Next →
                  </button>
                </div>
              )}
            </div>

            {/* Right: Team list */}
            <div className="w-full lg:w-1/2 bg-white rounded-lg shadow p-4 overflow-y-auto">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold text-ui-dark">Teams</h2>
                {selectedTeam && (
                  <button
                    onClick={handleAssessPlagiarism}
                    disabled={assessing}
                    className="px-3 py-1 text-sm rounded bg-primary text-white hover:bg-primary-hover transition-colors disabled:opacity-50"
                  >
                    {assessing ? "Assessing..." : `Assess ${selectedTeam}`}
                  </button>
                )}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {teamList.map((team) => {
                  const subs = submissions[team] || [];
                  return (
                    <button
                      key={team}
                      onClick={() => handleSelectTeam(team)}
                      className={`text-left px-3 py-2 rounded border transition-colors text-sm ${
                        team === selectedTeam
                          ? "bg-primary text-white border-primary"
                          : "bg-ui-lighter text-ui-dark border-ui-light hover:bg-ui-light"
                      }`}
                      title="View submissions"
                    >
                      <div className="font-medium truncate">{team}</div>
                      <div className="text-xs opacity-75">
                        {subs.length} submission{subs.length !== 1 ? "s" : ""}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Plagiarism assessment modal */}
      {report && (
        <div
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-6"
          onClick={() => setReport(null)}
        >
          <div
            className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[85vh] overflow-y-auto p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-xl font-bold text-ui-dark">
                  Assessment: {report.team_name}
                </h3>
                <div className="text-sm text-ui mt-1">
                  {report.submission_count_analyzed} of{" "}
                  {report.submission_count_total} submissions analyzed
                  {report.sampled && " (sampled)"} · model: {report.model_used}
                </div>
              </div>
              <button
                onClick={() => setReport(null)}
                className="text-ui hover:text-ui-dark text-2xl leading-none"
                aria-label="Close"
              >
                ×
              </button>
            </div>

            {/* Deterministic heuristic (computed locally, independent of the LLM). */}
            <div
              className={`mb-4 p-3 rounded border ${
                report.deterministic_concern_level === "likely_plagiarism"
                  ? "border-red-300 bg-red-50"
                  : report.deterministic_concern_level === "probable_plagiarism"
                  ? "border-yellow-300 bg-yellow-50"
                  : "border-green-300 bg-green-50"
              }`}
            >
              <div className="font-semibold text-ui-dark mb-1">
                Typing-speed heuristic:{" "}
                <span className={verdictColor(report.deterministic_concern_level)}>
                  {formatDeterministicLabel(report.deterministic_concern_level)}
                </span>
              </div>
              {report.deterministic_flag_summary &&
              report.deterministic_flag_summary.length > 0 ? (
                <ul className="list-disc ml-5 text-sm text-ui-dark">
                  {report.deterministic_flag_summary.map((line, i) => (
                    <li key={i}>{line}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-ui-dark">
                  All submission deltas are within normal typing speed (≤ 4 chars/sec).
                </p>
              )}
            </div>

            <div className="mb-4">
              <div className="font-semibold text-ui-dark mb-1">
                Progression:{" "}
                <span className={verdictColor(report.verdict.progression_verdict)}>
                  {report.verdict.progression_verdict}
                </span>
              </div>
              <p className="text-sm text-ui-dark whitespace-pre-wrap">
                {report.verdict.progression_reasoning}
              </p>
            </div>

            <div className="mb-4">
              <div className="font-semibold text-ui-dark mb-1">
                AI-generated:{" "}
                <span className={verdictColor(report.verdict.ai_generation_verdict)}>
                  {report.verdict.ai_generation_verdict}
                </span>
              </div>
              <p className="text-sm text-ui-dark whitespace-pre-wrap">
                {report.verdict.ai_generation_reasoning}
              </p>
            </div>

            <div className="mb-4">
              <div className="font-semibold text-ui-dark">
                Overall concern:{" "}
                <span className={verdictColor(report.verdict.overall_concern_level)}>
                  {report.verdict.overall_concern_level}
                </span>
              </div>
            </div>

            {report.verdict.specific_flags &&
              report.verdict.specific_flags.length > 0 && (
                <div className="mb-4">
                  <div className="font-semibold text-ui-dark mb-1">Flags:</div>
                  <ul className="list-disc ml-5 text-sm text-ui-dark">
                    {report.verdict.specific_flags.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              )}

            <details className="mt-4 text-xs">
              <summary className="cursor-pointer font-semibold text-ui-dark">
                Raw metrics
              </summary>
              <pre className="bg-gray-100 p-3 mt-2 rounded overflow-x-auto text-[11px]">
                {"Per-submission metrics:\n"}
                {JSON.stringify(report.submission_metrics, null, 2)}
                {"\n\nPairwise metrics:\n"}
                {JSON.stringify(report.pairwise_metrics, null, 2)}
              </pre>
            </details>

            <button
              onClick={() => setReport(null)}
              className="mt-4 px-4 py-2 bg-primary text-white rounded hover:bg-primary-hover transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default InstitutionLeagueSubmissions;
