import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import { toast } from "react-toastify";

import { setCurrentLeague, setLeagues } from "../../slices/leaguesSlice";
import useAuthAPI from "../Shared/hooks/useAuthAPI";
import CredentialsModal from "../Shared/Utilities/CredentialsModal";

function DirectSchoolLeagueSignup({ leagueToken, leagueInfo, onShowLogin }) {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { directSchoolSignup, isLoading } = useAuthAPI();

  const [formData, setFormData] = useState({
    schoolName: "",
    password: "",
    confirmPassword: "",
  });
  const [error, setError] = useState("");
  const [assignedTeamName, setAssignedTeamName] = useState(null);

  const schools = leagueInfo?.schools || [];

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.schoolName) {
      setError("Select your school");
      return;
    }
    if (!formData.password) {
      setError("Password is required");
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    const result = await directSchoolSignup(
      leagueToken,
      formData.schoolName,
      formData.password
    );

    if (result.success) {
      const leagueObject = {
        id: result.leagueId,
        name: leagueInfo.name,
        game: leagueInfo.game,
        created_date: leagueInfo.created_date,
        expiry_date: leagueInfo.expiry_date,
        school_league: true,
      };

      dispatch(setLeagues([leagueObject]));
      dispatch(setCurrentLeague(leagueInfo.name));

      setAssignedTeamName(result.teamName);
    } else {
      setError(result.error || "Failed to sign up");
    }
  };

  const handleDismissModal = () => {
    toast.success(`Signed up as ${assignedTeamName}.`);
    navigate("/TeamHome");
  };

  return (
    <>
      <div
        className="mb-6 bg-yellow-50 border-l-4 border-yellow-400 text-yellow-800 p-4 rounded"
        role="alert"
      >
        <p className="font-bold">Save your password now.</p>
        <p className="text-sm mt-1">
          There is no password recovery. If you lose your password you will
          need to sign up again and pick the next team number for your school.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="schoolName" className="block text-ui-dark mb-1">
            School
          </label>
          <select
            id="schoolName"
            name="schoolName"
            value={formData.schoolName}
            onChange={handleChange}
            className="w-full p-2 border border-ui-light rounded"
          >
            <option value="">Select your school...</option>
            {schools.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="password" className="block text-ui-dark mb-1">
            Password
          </label>
          <input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            className="w-full p-2 border border-ui-light rounded"
            placeholder="Choose a password"
          />
        </div>

        <div>
          <label htmlFor="confirmPassword" className="block text-ui-dark mb-1">
            Confirm Password
          </label>
          <input
            type="password"
            id="confirmPassword"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleChange}
            className="w-full p-2 border border-ui-light rounded"
            placeholder="Confirm your password"
          />
        </div>

        {error && <div className="text-red-600">{error}</div>}

        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:bg-gray-400"
        >
          {isLoading ? "Signing up..." : "Sign Up & Join League"}
        </button>
      </form>

      <div className="mt-4 text-center text-gray-600">
        <p>
          Already signed up?{" "}
          {onShowLogin ? (
            <button onClick={onShowLogin} className="text-blue-600">
              Log in
            </button>
          ) : (
            <a href="/AgentLogin" className="text-blue-600">
              Log in
            </a>
          )}
        </p>
      </div>

      {assignedTeamName && (
        <CredentialsModal
          teamName={assignedTeamName}
          password={formData.password}
          onDismiss={handleDismissModal}
        />
      )}
    </>
  );
}

export default DirectSchoolLeagueSignup;
