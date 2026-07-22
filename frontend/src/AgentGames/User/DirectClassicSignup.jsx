import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import { toast } from "react-toastify";

import { setCurrentLeague, setLeagues } from "../../slices/leaguesSlice";
import useAuthAPI from "../Shared/hooks/useAuthAPI";
import { getTerms } from "../Shared/terminology";
import CredentialsModal from "../Shared/Utilities/CredentialsModal";

function DirectClassicSignup({ leagueToken, leagueInfo, onShowLogin }) {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { directSignup, isLoading } = useAuthAPI();
  // Visitors are logged out, so wording comes from the league's institution.
  const T = getTerms(Boolean(leagueInfo?.is_teacher));

  const [formData, setFormData] = useState({
    teamName: "",
    password: "",
    confirmPassword: "",
    schoolName: "",
  });
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError("");
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!formData.teamName || !formData.password) {
      setError("All fields are required");
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setShowModal(true);
  };

  const handleConfirmSignup = async () => {
    setShowModal(false);

    const result = await directSignup(
      formData.teamName,
      formData.password,
      leagueToken,
      formData.schoolName,
    );

    if (result.success) {
      dispatch(
        setLeagues([
          {
            id: result.leagueId,
            name: leagueInfo.name,
            game: leagueInfo.game,
            created_date: leagueInfo.created_date,
            expiry_date: leagueInfo.expiry_date,
          },
        ]),
      );
      dispatch(setCurrentLeague(leagueInfo.name));

      toast.success(`Signed up and joined ${T.league} successfully!`);

      setTimeout(() => {
        navigate("/TeamHome");
      }, 300);
    } else {
      setError(result.error || "Failed to sign up");
    }
  };

  return (
    <>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="teamName" className="block text-ui-dark mb-1">
            {`${T.Team} Name`}
          </label>
          <input
            type="text"
            id="teamName"
            name="teamName"
            value={formData.teamName}
            onChange={handleChange}
            className="w-full p-2 border border-ui-light rounded"
            placeholder={`Choose a ${T.team} name`}
          />
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

        <div>
          <label htmlFor="schoolName" className="block text-ui-dark mb-1">
            School Name
          </label>
          <input
            type="text"
            id="schoolName"
            name="schoolName"
            value={formData.schoolName}
            onChange={handleChange}
            className="w-full p-2 border border-ui-light rounded"
            placeholder="Enter your school name in full"
          />
        </div>

        {error && <div className="text-red-600">{error}</div>}

        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:bg-gray-400"
        >
          {isLoading ? "Signing up..." : `Sign Up & Join ${T.League}`}
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

      {showModal && (
        <CredentialsModal
          teamName={formData.teamName}
          password={formData.password}
          onDismiss={handleConfirmSignup}
        />
      )}
    </>
  );
}

export default DirectClassicSignup;
