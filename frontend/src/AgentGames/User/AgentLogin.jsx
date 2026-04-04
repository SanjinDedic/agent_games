import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { checkTokenExpiry } from "../../slices/authSlice";
import UserTooltip from "../Shared/Utilities/UserTooltips";
import InstructionPopup from "../Shared/Utilities/InstructionPopup";
import useAuthAPI from "../Shared/hooks/useAuthAPI";

function AgentLogin() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const currentUser = useSelector((state) => state.auth.currentUser);
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);

  const [institutions, setInstitutions] = useState([]);
  const [selectedInstitution, setSelectedInstitution] = useState(null);
  const [team, setTeam] = useState({ name: "", password: "" });
  const [errorMessage, setErrorMessage] = useState("");
  const [shake, setShake] = useState(false);
  const [loadingInstitutions, setLoadingInstitutions] = useState(true);

  const { teamLogin, isLoading } = useAuthAPI();

  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (isAuthenticated && !tokenExpired && currentUser.role === "student") {
      navigate("/AgentLeagueSignUp");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const fetchInstitutions = async () => {
      try {
        const response = await fetch(`${apiUrl}/auth/institutions`);
        const data = await response.json();
        if (data.status === "success") {
          setInstitutions(data.data.institutions);
        }
      } catch (error) {
        console.error('Error fetching institutions:', error);
      } finally {
        setLoadingInstitutions(false);
      }
    };
    fetchInstitutions();
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
      navigate("/AgentLeagueSignUp");
    } else {
      setErrorMessage(result.error || "Login failed");
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleLogin();
    }
  };

  const inputClasses = `w-full px-4 py-2 text-lg rounded-lg transition-all duration-200
    border border-ui-light/20 focus:outline-none focus:ring-1 focus:ring-primary/30
    ${shake ? 'animate-shake border-danger' : 'focus:border-primary/30'}`;

  return (
    <div className="min-h-screen pt-16 flex flex-col items-center justify-center bg-ui-lighter">
      <div className="w-full max-w-[800px] px-4">
        <InstructionPopup homescreen={true} />

        {!selectedInstitution ? (
          <div className="bg-white rounded-lg shadow-lg p-8 border border-ui-light/10">
            <h2 className="text-2xl font-semibold text-ui-dark mb-6 text-center">
              Select Your Institution
            </h2>

            {loadingInstitutions ? (
              <p className="text-center text-ui-dark/60">Loading institutions...</p>
            ) : institutions.length === 0 ? (
              <p className="text-center text-ui-dark/60">No institutions available</p>
            ) : (
              <div className="space-y-3">
                {institutions.map((name) => (
                  <button
                    key={name}
                    onClick={() => {
                      setSelectedInstitution(name);
                      setErrorMessage("");
                    }}
                    className="w-full py-4 px-6 text-lg font-medium text-left rounded-lg border border-ui-light/20 hover:border-primary hover:bg-primary/5 transition-all duration-200"
                  >
                    {name}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-lg p-8 border border-ui-light/10">
            <button
              onClick={() => {
                setSelectedInstitution(null);
                setTeam({ name: "", password: "" });
                setErrorMessage("");
              }}
              className="text-primary hover:text-primary-hover text-sm font-medium mb-4 flex items-center gap-1"
            >
              &larr; Back to institutions
            </button>

            <h2 className="text-2xl font-semibold text-ui-dark mb-6 text-center">
              {selectedInstitution}
            </h2>

            <div className="space-y-6">
              <div className="space-y-2">
                <label className="block text-xl font-medium text-ui-dark">
                  Username:
                </label>
                <input
                  type="text"
                  id="team_name"
                  name="name"
                  onChange={handleChange}
                  onKeyDown={handleKeyDown}
                  className={inputClasses}
                  placeholder="Enter your username"
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

              <UserTooltip
                title="&#9888;&#65039; INFO <br />Enter your login details provided by your teacher or school and then login."
                arrow
                disableFocusListener
                disableTouchListener
              >
                <button
                  onClick={handleLogin}
                  disabled={isLoading}
                  className="w-full py-3 px-4 text-lg font-medium text-white bg-primary hover:bg-primary-hover rounded-lg transition-colors duration-200 disabled:bg-ui-light disabled:cursor-not-allowed"
                >
                  {isLoading ? "Logging in..." : "Login"}
                </button>
              </UserTooltip>

              {errorMessage && (
                <p className="text-lg text-danger text-center">{errorMessage}</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default AgentLogin;
