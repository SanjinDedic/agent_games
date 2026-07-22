import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import {
  selectCurrentUser,
  selectIsAuthenticated,
  selectIsTokenExpired,
} from "../../slices/authSlice";
import useAuthAPI from "../Shared/hooks/useAuthAPI";

// Icons are set per competition by the admin: an emoji, or an image URL.
function CompetitionIcon({ icon }) {
  if (icon && /^(https?:\/\/|\/)/.test(icon)) {
    return (
      <img
        src={icon}
        alt=""
        className="h-10 w-10 object-contain rounded shrink-0"
      />
    );
  }
  return (
    <span className="text-3xl leading-none shrink-0" aria-hidden="true">
      {icon || "🏆"}
    </span>
  );
}

// Student/team login entry point. Students first say what brought them here:
// classroom students are pointed at their teacher's shareable /join/<token>
// page (they never pick from a list), competition entrants pick their
// competition and log in with name + password.
function AgentLogin() {
  const navigate = useNavigate();
  const currentUser = useSelector(selectCurrentUser);
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const tokenExpired = useSelector(selectIsTokenExpired);
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);

  const [mode, setMode] = useState(null); // null | "classroom" | "competition"
  const [competitions, setCompetitions] = useState([]);
  const [selectedCompetition, setSelectedCompetition] = useState(null);
  const [team, setTeam] = useState({ name: "", password: "" });
  const [errorMessage, setErrorMessage] = useState("");
  const [shake, setShake] = useState(false);
  const [loadingCompetitions, setLoadingCompetitions] = useState(true);

  const { teamLogin, isLoading } = useAuthAPI();

  useEffect(() => {
    if (isAuthenticated && !tokenExpired && currentUser.role === "student") {
      navigate("/TeamHome");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const fetchCompetitions = async () => {
      try {
        const response = await fetch(`${apiUrl}/auth/competitions`);
        const data = await response.json();
        if (response.ok) {
          setCompetitions(data.competitions);
        }
      } catch (error) {
        console.error('Error fetching competitions:', error);
      } finally {
        setLoadingCompetitions(false);
      }
    };
    fetchCompetitions();
  }, [apiUrl]);

  const handleChange = (e) => {
    setTeam((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
    setErrorMessage("");
  };

  const handleLogin = async () => {
    if (!team.name.trim() || !team.password.trim()) {
      setShake(true);
      setTimeout(() => setShake(false), 1000);
      setErrorMessage("Please enter all the fields");
      return;
    }

    const result = await teamLogin(team.name, team.password);

    if (result.success) {
      // TeamHome bounces unassigned students to the league picker itself.
      navigate("/TeamHome");
    } else {
      setErrorMessage(result.error || "Login failed");
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleLogin();
    }
  };

  const backTo = (target) => () => {
    setMode(target);
    setSelectedCompetition(null);
    setTeam({ name: "", password: "" });
    setErrorMessage("");
  };

  const inputClasses = `w-full px-4 py-2 text-lg rounded-lg transition-all duration-200
    border border-ui-light/20 focus:outline-none focus:ring-1 focus:ring-primary/30
    ${shake ? 'animate-shake border-danger' : 'focus:border-primary/30'}`;

  const backButtonClasses =
    "text-primary hover:text-primary-hover text-sm font-medium mb-4 flex items-center gap-1";

  return (
    <div className="min-h-screen pt-16 flex flex-col items-center justify-center bg-ui-lighter">
      <div className="w-full max-w-[600px] px-4">
        {mode === null && (
          <div className="bg-white rounded-lg shadow-lg p-8 border border-ui-light/10">
            <h2 className="text-2xl font-semibold text-ui-dark mb-2 text-center">
              Welcome! What are you here for?
            </h2>
            <p className="text-ui-dark/60 text-center mb-8">
              Pick one so we can get you to the right login.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <button
                onClick={() => setMode("classroom")}
                className="flex flex-col items-center gap-3 py-8 px-6 rounded-lg border border-ui-light/20 hover:border-primary hover:bg-primary/5 transition-all duration-200"
              >
                <span className="text-5xl" aria-hidden="true">🏫</span>
                <span className="text-xl font-semibold text-ui-dark">
                  Classroom
                </span>
                <span className="text-sm text-ui-dark/60 text-center">
                  I'm doing Agent Games with my class
                </span>
              </button>

              <button
                onClick={() => setMode("competition")}
                className="flex flex-col items-center gap-3 py-8 px-6 rounded-lg border border-ui-light/20 hover:border-primary hover:bg-primary/5 transition-all duration-200"
              >
                <span className="text-5xl" aria-hidden="true">🏆</span>
                <span className="text-xl font-semibold text-ui-dark">
                  Competition
                </span>
                <span className="text-sm text-ui-dark/60 text-center">
                  I'm entered in a coding competition
                </span>
              </button>
            </div>
          </div>
        )}

        {mode === "classroom" && (
          <div className="bg-white rounded-lg shadow-lg p-8 border border-ui-light/10">
            <button onClick={backTo(null)} className={backButtonClasses}>
              &larr; Back
            </button>

            <div className="text-center space-y-4">
              <span className="text-5xl block" aria-hidden="true">🏫</span>
              <h2 className="text-2xl font-semibold text-ui-dark">
                Your class has its own login page
              </h2>
              <p className="text-ui-dark/70 text-lg">
                Ask your teacher to share your classroom's login link. It looks
                like:
              </p>
              <p className="font-mono text-ui-dark bg-ui-lighter rounded-lg py-2 px-4 inline-block">
                {window.location.origin}/join/...
              </p>
              <p className="text-ui-dark/70 text-lg">
                Open that link to sign up or log in — it takes you straight
                into your class.
              </p>
            </div>
          </div>
        )}

        {mode === "competition" && !selectedCompetition && (
          <div className="bg-white rounded-lg shadow-lg p-8 border border-ui-light/10">
            <button onClick={backTo(null)} className={backButtonClasses}>
              &larr; Back
            </button>

            <h2 className="text-2xl font-semibold text-ui-dark mb-6 text-center">
              Select Your Competition
            </h2>

            {loadingCompetitions ? (
              <p className="text-center text-ui-dark/60">
                Loading competitions...
              </p>
            ) : competitions.length === 0 ? (
              <p className="text-center text-ui-dark/60">
                No competitions are running right now
              </p>
            ) : (
              <div className="space-y-3">
                {competitions.map((competition) => (
                  <button
                    key={competition.name}
                    onClick={() => {
                      setSelectedCompetition(competition);
                      setErrorMessage("");
                    }}
                    className="w-full py-4 px-6 flex items-center gap-4 text-lg font-medium text-left rounded-lg border border-ui-light/20 hover:border-primary hover:bg-primary/5 transition-all duration-200"
                  >
                    <CompetitionIcon icon={competition.icon} />
                    <span>{competition.name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {mode === "competition" && selectedCompetition && (
          <div className="bg-white rounded-lg shadow-lg p-8 border border-ui-light/10">
            <button
              onClick={backTo("competition")}
              className={backButtonClasses}
            >
              &larr; Back to competitions
            </button>

            <div className="flex items-center justify-center gap-3 mb-6">
              <CompetitionIcon icon={selectedCompetition.icon} />
              <h2 className="text-2xl font-semibold text-ui-dark text-center">
                {selectedCompetition.name}
              </h2>
            </div>

            <div className="space-y-6">
              <div className="space-y-2">
                <label className="block text-xl font-medium text-ui-dark">
                  Name:
                </label>
                <input
                  type="text"
                  id="team_name"
                  name="name"
                  onChange={handleChange}
                  onKeyDown={handleKeyDown}
                  className={inputClasses}
                  placeholder="Enter your team name"
                  autoFocus
                />
              </div>

              <div className="space-y-2">
                <label className="block text-xl font-medium text-ui-dark">
                  Password:
                </label>
                <input
                  type="password"
                  id="team_password"
                  name="password"
                  onChange={handleChange}
                  onKeyDown={handleKeyDown}
                  className={inputClasses}
                  placeholder="Enter your password"
                />
              </div>

              <button
                onClick={handleLogin}
                disabled={isLoading}
                className="w-full py-3 px-4 text-lg font-medium text-white bg-primary hover:bg-primary-hover rounded-lg transition-colors duration-200 disabled:bg-ui-light disabled:cursor-not-allowed"
              >
                {isLoading ? "Logging in..." : "Login"}
              </button>

              {errorMessage && (
                <p className="text-lg text-danger text-center">{errorMessage}</p>
              )}
            </div>
          </div>
        )}

        <div className="mt-6 text-center text-ui-dark/60 space-y-2">
          <p>
            <Link
              to="/Teacher"
              className="text-primary hover:text-primary-hover font-medium"
            >
              Teacher login
            </Link>
            {" · "}
            <Link
              to="/Institution"
              className="text-primary hover:text-primary-hover font-medium"
            >
              Competition organizer login
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default AgentLogin;
