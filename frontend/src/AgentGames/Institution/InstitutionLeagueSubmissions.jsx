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
    case "normal":
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
    case "highly_suspicious":
      return "text-red-600";
    case "not_applicable":
      return "text-gray-500";
    default:
      return "text-ui-dark";
  }
};

const formatConcernLabel = (level) => {
  if (level === "likely_plagiarism") return "most likely plagiarising";
  if (level === "probable_plagiarism") return "probably plagiarising";
  return "no concerns";
};

/**
 * A horizontal bar with colored zones and a dot marker showing the actual value.
 * zones: [{end: number, bg: string}] — cumulative thresholds left-to-right.
 */
const ContinuumBar = ({ value, max, zones, label, unit = "" }) => {
  const clamped = Math.min(Math.max(value ?? 0, 0), max);
  const pct = (clamped / max) * 100;

  return (
    <div className="flex items-center gap-2 mb-1">
      <div className="flex-1 h-3 rounded-full overflow-hidden relative flex border border-gray-300">
        {zones.map((zone, i) => {
          const prevEnd = i === 0 ? 0 : zones[i - 1].end;
          const width = ((zone.end - prevEnd) / max) * 100;
          return (
            <div key={i} className={`h-full ${zone.bg}`} style={{ width: `${width}%` }} />
          );
        })}
        {/* Marker dot */}
        {value != null && (
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3.5 h-3.5 bg-gray-800 rounded-full border-2 border-white shadow"
            style={{ left: `${pct}%` }}
          />
        )}
      </div>
      <span className="text-xs font-mono w-20 text-right text-gray-700">
        {value != null ? `${value}${unit}` : "n/a"}
      </span>
    </div>
  );
};

// Zone definitions for each metric
const CPS_ZONES = [
  { end: 4, bg: "bg-green-200" },
  { end: 6, bg: "bg-yellow-200" },
  { end: 8, bg: "bg-red-300" },
];
const CPS_MAX = 8;

const AST_ZONES = [
  { end: 8, bg: "bg-green-200" },
  { end: 15, bg: "bg-yellow-200" },
  { end: 20, bg: "bg-red-300" },
];
const AST_MAX = 20;

// Template similarity is inverted (high = good): Red → Yellow → Green
const TEMPLATE_ZONES = [
  { end: 30, bg: "bg-red-300" },
  { end: 50, bg: "bg-yellow-200" },
  { end: 100, bg: "bg-green-200" },
];
const TEMPLATE_MAX = 100;

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

            {/* ===== TOP HALF: Deterministic Analysis ===== */}
            <div className="mb-5 pb-5 border-b border-gray-200">
              <div className="flex items-center gap-2 mb-3">
                <h4 className="font-bold text-gray-800">Deterministic Analysis</h4>
                <span
                  className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                    report.deterministic_concern_level === "likely_plagiarism"
                      ? "bg-red-100 text-red-700"
                      : report.deterministic_concern_level === "probable_plagiarism"
                      ? "bg-yellow-100 text-yellow-700"
                      : "bg-green-100 text-green-700"
                  }`}
                >
                  {formatConcernLabel(report.deterministic_concern_level)}
                </span>
              </div>

              {/* Template similarity (per-submission) */}
              {report.submission_metrics.some((s) => s.template_similarity != null) && (
                <div className="mb-4">
                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                    Template Similarity
                  </div>
                  {report.submission_metrics.map((sm) =>
                    sm.template_similarity != null ? (
                      <div key={sm.index} className="flex items-center gap-2">
                        <span className="text-xs text-gray-500 w-24 shrink-0">
                          submission {sm.index + 1}
                        </span>
                        <div className="flex-1">
                          <ContinuumBar
                            value={Math.round(sm.template_similarity * 100)}
                            max={TEMPLATE_MAX}
                            zones={TEMPLATE_ZONES}
                            label={`${Math.round(sm.template_similarity * 100)}%`}
                          />
                        </div>
                      </div>
                    ) : null
                  )}
                </div>
              )}

              {/* Per-pair bars: chars/sec + AST constructs */}
              {report.pairwise_metrics.length > 0 && (
                <div className="space-y-3">
                  {report.pairwise_metrics.map((pm) => (
                    <div
                      key={`${pm.from_index}-${pm.to_index}`}
                      className="bg-gray-50 rounded p-3"
                    >
                      <div className="text-xs font-semibold text-gray-600 mb-2">
                        submission {pm.from_index + 1} → submission {pm.to_index + 1}
                        <span className="font-normal text-gray-400 ml-2">
                          ({Math.round(pm.elapsed_seconds)}s elapsed ·{" "}
                          +{pm.chars_added} / −{pm.chars_removed} chars)
                        </span>
                      </div>

                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs text-gray-500 w-24 shrink-0">
                          Chars / sec
                        </span>
                        <div className="flex-1">
                          <ContinuumBar
                            value={pm.chars_added_per_second}
                            max={CPS_MAX}
                            zones={CPS_ZONES}
                            label={
                              pm.chars_added_per_second != null
                                ? `${pm.chars_added_per_second}`
                                : "n/a"
                            }
                          />
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500 w-24 shrink-0">
                          Complexity Δ
                        </span>
                        <div className="flex-1">
                          <ContinuumBar
                            value={pm.constructs_added}
                            max={AST_MAX}
                            zones={AST_ZONES}
                            label={`+${pm.constructs_added}`}
                          />
                        </div>
                      </div>

                      {pm.new_construct_types && pm.new_construct_types.length > 0 && (
                        <div className="text-[11px] text-gray-400 mt-1 ml-26">
                          New: {pm.new_construct_types.join(", ")}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Text summary of all deterministic flags */}
              {report.deterministic_flag_summary &&
                report.deterministic_flag_summary.length > 0 && (
                  <div className="mt-3 text-xs text-gray-600">
                    <div className="font-semibold mb-1">Summary:</div>
                    <ul className="list-disc ml-5 space-y-0.5">
                      {report.deterministic_flag_summary.map((line, i) => (
                        <li key={i}>{line}</li>
                      ))}
                    </ul>
                  </div>
                )}
            </div>

            {/* ===== BOTTOM HALF: LLM Verdict ===== */}
            <div>
              <h4 className="font-bold text-gray-800 mb-3">AI Analysis</h4>

              <div className="mb-3">
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

              <div className="mb-3">
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

              <div className="mb-3">
                <div className="font-semibold text-ui-dark">
                  Overall concern:{" "}
                  <span className={verdictColor(report.verdict.overall_concern_level)}>
                    {report.verdict.overall_concern_level}
                  </span>
                </div>
              </div>

              {report.verdict.specific_flags &&
                report.verdict.specific_flags.length > 0 && (
                  <div className="mb-3">
                    <div className="font-semibold text-ui-dark mb-1">Flags:</div>
                    <ul className="list-disc ml-5 text-sm text-ui-dark">
                      {report.verdict.specific_flags.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  </div>
                )}
            </div>

            <details className="mt-4 text-xs border-t border-gray-200 pt-3">
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
