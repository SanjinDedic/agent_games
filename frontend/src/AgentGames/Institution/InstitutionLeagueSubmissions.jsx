// src/AgentGames/Institution/InstitutionLeagueSubmissions.jsx
import React, { useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, useParams } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { checkTokenExpiry } from "../../slices/authSlice";
import { authFetch } from "../../utils/authFetch";

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
              <h2 className="text-lg font-semibold text-ui-dark mb-3">Teams</h2>
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
    </div>
  );
}

export default InstitutionLeagueSubmissions;
