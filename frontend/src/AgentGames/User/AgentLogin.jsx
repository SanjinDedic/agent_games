import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import {
  selectCurrentUser,
  selectIsAuthenticated,
  selectIsTokenExpired,
} from "../../slices/authSlice";
import { selectSiteIcon, selectSiteName } from "../../slices/settingsSlice";
import useAuthAPI from "../Shared/hooks/useAuthAPI";
import { useTerms } from "../Shared/terminology";

// Site icon: an emoji, or an image URL, from SITE_ICON.
function SiteIcon({ icon }) {
  if (!icon) return null;
  if (/^(https?:\/\/|\/)/.test(icon)) {
    return (
      <img src={icon} alt="" className="h-12 w-12 object-contain rounded mx-auto" />
    );
  }
  return (
    <span className="text-5xl leading-none block text-center" aria-hidden="true">
      {icon}
    </span>
  );
}

// Team login. There used to be a two-step picker here — first "classroom or
// competition?", then which competition — because one deployment hosted many.
// It hosts one, so the picker is a name and a password.
function AgentLogin() {
  const T = useTerms();
  const navigate = useNavigate();
  const currentUser = useSelector(selectCurrentUser);
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const tokenExpired = useSelector(selectIsTokenExpired);
  const siteName = useSelector(selectSiteName);
  const siteIcon = useSelector(selectSiteIcon);

  const [team, setTeam] = useState({ name: "", password: "" });
  const [errorMessage, setErrorMessage] = useState("");
  const [shake, setShake] = useState(false);

  const { teamLogin, isLoading } = useAuthAPI();

  useEffect(() => {
    if (isAuthenticated && !tokenExpired && currentUser.role === "student") {
      navigate("/TeamHome");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (e) => {
    setTeam((prev) => ({ ...prev, [e.target.name]: e.target.value }));
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
      // An admin logging in here rather than at /Login is a wrong-door mistake,
      // not a failure — send them where their token works (AdminLogin does the
      // same for a team that lands on it).
      navigate(result.role === "admin" ? "/Home" : "/TeamHome");
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
      <div className="w-full max-w-[480px] px-4">
        <div className="bg-white rounded-lg shadow-lg p-8 border border-ui-light/10">
          <SiteIcon icon={siteIcon} />
          <h2 className="text-2xl font-semibold text-ui-dark mt-3 mb-8 text-center">
            {siteName}
          </h2>

          <div className="space-y-5">
            <div className="space-y-2">
              <label
                htmlFor="team_name"
                className="text-base font-medium text-ui-dark"
              >
                {`${T.Team} name`}
              </label>
              <input
                type="text"
                id="team_name"
                name="name"
                autoComplete="username"
                value={team.name}
                onChange={handleChange}
                onKeyDown={handleKeyDown}
                className={inputClasses}
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="team_password"
                className="text-base font-medium text-ui-dark"
              >
                Password
              </label>
              <input
                type="password"
                id="team_password"
                name="password"
                autoComplete="current-password"
                value={team.password}
                onChange={handleChange}
                onKeyDown={handleKeyDown}
                className={inputClasses}
              />
            </div>

            <button
              onClick={handleLogin}
              disabled={isLoading}
              className="w-full py-3 px-6 text-lg font-semibold text-white bg-primary hover:bg-primary-hover disabled:opacity-60 rounded-lg transition-colors duration-200"
            >
              {isLoading ? "Logging in…" : "Login"}
            </button>

            {errorMessage && (
              <p className="text-base text-danger text-center">{errorMessage}</p>
            )}
          </div>

          <p className="text-sm text-ui-dark/60 text-center mt-8">
            {`No account yet? Ask for your ${T.league}'s join link.`}
          </p>
        </div>

        <p className="text-sm text-ui-dark/60 text-center mt-6">
          Running this site?{" "}
          <Link to="/Login" className="text-primary hover:text-primary-hover">
            Admin login
          </Link>
        </p>
      </div>
    </div>
  );
}

export default AgentLogin;
