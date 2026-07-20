import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useSelector } from "react-redux";

import {
  selectCurrentUser,
  selectIsAuthenticated,
  selectIsTokenExpired,
} from "../../slices/authSlice";
import useAuthAPI from "../Shared/hooks/useAuthAPI";
import useLeagueAPI from "../Shared/hooks/useLeagueAPI";
import { getTerms } from "../Shared/terminology";
import DirectClassicSignup from "./DirectClassicSignup";
import DirectSchoolLeagueSignup from "./DirectSchoolLeagueSignup";

// Every classroom/league has one shareable page: students sign up here the
// first time, log in here afterwards, and always land inside this league.
// /join/:leagueToken opens on the login tab; the legacy /TeamSignup route
// opens on signup so old shared links keep their meaning.
function ClassroomJoin({ defaultTab = "login" }) {
  const { leagueToken } = useParams();
  const navigate = useNavigate();
  const { getLeagueInfo, fetchUserLeagues, assignToLeague } = useLeagueAPI();
  const { teamLogin, isLoading } = useAuthAPI();

  const currentUser = useSelector(selectCurrentUser);
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const tokenExpired = useSelector(selectIsTokenExpired);

  const [leagueInfo, setLeagueInfo] = useState(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState(defaultTab);
  const [credentials, setCredentials] = useState({ name: "", password: "" });
  const [loginError, setLoginError] = useState("");
  const [routing, setRouting] = useState(false);
  const [conflictLeague, setConflictLeague] = useState(null);

  // Wording comes from the league's owning institution, not the session:
  // visitors here are usually logged out.
  const T = getTerms(Boolean(leagueInfo?.is_teacher));

  const isStudentSession =
    isAuthenticated && !tokenExpired && currentUser.role === "student";

  useEffect(() => {
    const fetchLeagueInfo = async () => {
      if (!leagueToken) return;

      const result = await getLeagueInfo(leagueToken);
      if (result.success) {
        setLeagueInfo(result.data);
      } else {
        setError("Invalid link, or this page is no longer active");
      }
    };

    fetchLeagueInfo();
  }, [leagueToken, getLeagueInfo]);

  // Route an authenticated student into this league. Runs on the render after
  // login so the API hooks hold the fresh token. Students assigned elsewhere
  // get an explicit choice instead of being moved silently.
  useEffect(() => {
    if (!routing || !leagueInfo || !isStudentSession) return;

    if (currentUser.league_id === leagueInfo.id) {
      navigate("/AgentSubmission");
      return;
    }

    let cancelled = false;
    (async () => {
      const result = await fetchUserLeagues();
      if (cancelled) return;
      if (!result.success) {
        setRouting(false);
        return;
      }

      const assigned = result.leagues.find(
        (l) => l.id === currentUser.league_id
      );
      if (assigned && assigned.name.toLowerCase() !== "unassigned") {
        setConflictLeague(assigned);
        setRouting(false);
        return;
      }

      const assign = await assignToLeague(leagueInfo.id);
      if (cancelled) return;
      navigate(assign.success ? "/AgentSubmission" : "/AgentLeagueSignUp");
    })();

    return () => {
      cancelled = true;
    };
  }, [
    routing,
    leagueInfo,
    isStudentSession,
    currentUser.league_id,
    fetchUserLeagues,
    assignToLeague,
    navigate,
  ]);

  const handleChange = (e) => {
    setCredentials((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setLoginError("");
  };

  const handleLogin = async () => {
    if (!credentials.name.trim() || !credentials.password.trim()) {
      setLoginError("Please enter your name and password");
      return;
    }

    const result = await teamLogin(credentials.name, credentials.password);
    if (result.success) {
      setRouting(true);
    } else {
      setLoginError(result.error || "Login failed");
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleLogin();
  };

  const handleSwitchLeague = async () => {
    const result = await assignToLeague(leagueInfo.id);
    if (result.success) navigate("/AgentSubmission");
  };

  const tabClasses = (active) =>
    `flex-1 py-2 text-lg font-medium rounded-t-lg transition-colors duration-200 ${
      active
        ? "bg-white text-primary border-b-2 border-primary"
        : "bg-ui-lighter text-ui-dark/60 hover:text-ui-dark"
    }`;

  const inputClasses = `w-full px-4 py-2 text-lg rounded-lg transition-all duration-200
    border border-ui-light/20 focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary/30`;

  return (
    <div className="min-h-screen pt-16 flex flex-col items-center justify-center bg-ui-lighter">
      <div className="w-full max-w-md px-4">
        <div className="bg-white rounded-lg shadow-lg p-8">
          {leagueInfo ? (
            <>
              <div className="mb-6 text-center">
                <p className="text-sm uppercase tracking-wide text-ui-dark/60">
                  {leagueInfo.institution_name || `Agent Games ${T.League}`}
                </p>
                <h1 className="text-2xl font-bold text-ui-dark">
                  {leagueInfo.name}
                </h1>
                <p className="text-ui-dark/70">
                  {`${T.League} · ${leagueInfo.game}`}
                </p>
              </div>

              {conflictLeague ? (
                <div className="space-y-4">
                  <p className="text-ui-dark">
                    {`You're currently in `}
                    <span className="font-semibold">{conflictLeague.name}</span>
                    {`. Do you want to switch to `}
                    <span className="font-semibold">{leagueInfo.name}</span>?
                  </p>
                  <button
                    onClick={handleSwitchLeague}
                    className="w-full py-3 px-4 text-lg font-medium text-white bg-primary hover:bg-primary-hover rounded-lg transition-colors duration-200"
                  >
                    {`Switch to ${leagueInfo.name}`}
                  </button>
                  <button
                    onClick={() => navigate("/AgentSubmission")}
                    className="w-full py-3 px-4 text-lg font-medium text-ui-dark bg-ui-lighter hover:bg-ui-light rounded-lg transition-colors duration-200"
                  >
                    {`Stay in ${conflictLeague.name}`}
                  </button>
                </div>
              ) : isStudentSession ? (
                <div className="space-y-4 text-center">
                  <p className="text-ui-dark">
                    {`You're logged in as `}
                    <span className="font-semibold">{currentUser.name}</span>.
                  </p>
                  <button
                    onClick={() => setRouting(true)}
                    disabled={routing}
                    className="w-full py-3 px-4 text-lg font-medium text-white bg-primary hover:bg-primary-hover rounded-lg transition-colors duration-200 disabled:bg-ui-light"
                  >
                    {routing ? "Loading..." : `Continue to ${leagueInfo.name}`}
                  </button>
                  <p className="text-sm text-ui-dark/60">
                    Not you? Log out from the top bar first.
                  </p>
                </div>
              ) : (
                <>
                  <div className="flex mb-6 border-b border-ui-light/30">
                    <button
                      onClick={() => setTab("login")}
                      className={tabClasses(tab === "login")}
                    >
                      Log in
                    </button>
                    <button
                      onClick={() => setTab("signup")}
                      className={tabClasses(tab === "signup")}
                    >
                      Sign up
                    </button>
                  </div>

                  {tab === "login" ? (
                    <div className="space-y-5">
                      <div className="space-y-2">
                        <label className="block text-lg font-medium text-ui-dark">
                          Name:
                        </label>
                        <input
                          type="text"
                          name="name"
                          value={credentials.name}
                          onChange={handleChange}
                          onKeyDown={handleKeyDown}
                          className={inputClasses}
                          placeholder={`Your ${T.team} name`}
                          autoFocus
                        />
                      </div>

                      <div className="space-y-2">
                        <label className="block text-lg font-medium text-ui-dark">
                          Password:
                        </label>
                        <input
                          type="password"
                          name="password"
                          value={credentials.password}
                          onChange={handleChange}
                          onKeyDown={handleKeyDown}
                          className={inputClasses}
                          placeholder="Your password"
                        />
                      </div>

                      <button
                        onClick={handleLogin}
                        disabled={isLoading || routing}
                        className="w-full py-3 px-4 text-lg font-medium text-white bg-primary hover:bg-primary-hover rounded-lg transition-colors duration-200 disabled:bg-ui-light disabled:cursor-not-allowed"
                      >
                        {isLoading || routing ? "Logging in..." : "Log in"}
                      </button>

                      {loginError && (
                        <p className="text-danger text-center">{loginError}</p>
                      )}

                      <p className="text-center text-ui-dark/60">
                        First time here?{" "}
                        <button
                          onClick={() => setTab("signup")}
                          className="text-primary hover:text-primary-hover font-medium"
                        >
                          Sign up
                        </button>
                      </p>
                    </div>
                  ) : leagueInfo.school_league ? (
                    <DirectSchoolLeagueSignup
                      leagueToken={leagueToken}
                      leagueInfo={leagueInfo}
                      onShowLogin={() => setTab("login")}
                    />
                  ) : (
                    <DirectClassicSignup
                      leagueToken={leagueToken}
                      leagueInfo={leagueInfo}
                      onShowLogin={() => setTab("login")}
                    />
                  )}
                </>
              )}
            </>
          ) : error ? (
            <div className="text-center text-danger p-4">
              <p>{error}</p>
              <p className="mt-2">
                <a href="/" className="text-primary hover:text-primary-hover">
                  Return to home page
                </a>
              </p>
            </div>
          ) : (
            <div className="text-center p-4">
              <p className="text-ui-dark/60">Loading...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ClassroomJoin;
