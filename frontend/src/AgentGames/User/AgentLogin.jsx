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

  const [team, setTeam] = useState({ name: "", password: "" });
  const [errorMessage, setErrorMessage] = useState("");
  const [shake, setShake] = useState(false);

  // Use the authentication hook
  const { teamLogin, isLoading } = useAuthAPI();

  useEffect(() => {
    const tokenExpired = dispatch(checkTokenExpiry());
    if (isAuthenticated && !tokenExpired && currentUser.role === "student") {
      navigate("/AgentLeagueSignUp");
    }
  }, [navigate, dispatch, isAuthenticated, currentUser]);

  const handleChange = (e) => {
    setTeam((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
    setErrorMessage("");
  };

  const handleLogin = async () => {
    // Basic validation
    if (!team.name.trim() || !team.password.trim()) {
      setShake(true);
      setTimeout(() => setShake(false), 1000);
      setErrorMessage("Please Enter all the fields");
      return;
    }

    // Call the login API using our hook
    const result = await teamLogin(team.name, team.password);

    if (result.success) {
      navigate("/AgentLeagueSignUp");
    } else {
      setErrorMessage(result.error || "Login failed");
    }
  };

  const inputClasses = `w-full px-4 py-2 text-lg rounded-lg transition-all duration-200 
    border border-ui-light/20 focus:outline-none focus:ring-1 focus:ring-primary/30
    ${shake ? 'animate-shake border-danger' : 'focus:border-primary/30'}`;

  return (
    <div className="min-h-screen pt-16 flex flex-col items-center justify-center bg-ui-lighter">
      <div className="w-full max-w-[800px] px-4">
        <InstructionPopup homescreen={true} />

        <div className="bg-white rounded-lg shadow-lg p-8 border border-ui-light/10">
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
                className={inputClasses}
                placeholder="Enter your username"
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
                className={inputClasses}
                placeholder="Enter your password"
              />
            </div>

            <UserTooltip
              title="⚠️ INFO <br />Enter your login details provided by your teacher or school and then login."
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
      </div>
    </div>
  );
}

export default AgentLogin;