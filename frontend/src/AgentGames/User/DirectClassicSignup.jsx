import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import { toast } from "react-toastify";

import { setCurrentLeague, setLeagues } from "../../slices/leaguesSlice";
import useAuthAPI from "../Shared/hooks/useAuthAPI";

function DirectClassicSignup({ leagueToken, leagueInfo }) {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { directSignup, isLoading } = useAuthAPI();

  const [formData, setFormData] = useState({
    teamName: "",
    password: "",
    confirmPassword: "",
    schoolName: "",
  });
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.teamName || !formData.password) {
      setError("All fields are required");
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      return;
    }

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

      toast.success("Signed up and joined league successfully!");

      setTimeout(() => {
        navigate("/AgentSubmission");
      }, 300);
    } else {
      setError(result.error || "Failed to sign up");
    }
  };

  return (
    <>
      <div className="mb-6 bg-blue-100 p-4 rounded-lg">
        <h2 className="text-lg font-semibold text-blue-700">
          Joining League: {leagueInfo.name}
        </h2>
        <p className="text-gray-700">Game: {leagueInfo.game}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="teamName" className="block text-ui-dark mb-1">
            Team Name
          </label>
          <input
            type="text"
            id="teamName"
            name="teamName"
            value={formData.teamName}
            onChange={handleChange}
            className="w-full p-2 border border-ui-light rounded"
            placeholder="Choose a team name"
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
          {isLoading ? "Signing up..." : "Sign Up & Join League"}
        </button>
      </form>

      <div className="mt-4 text-center text-gray-600">
        <p>
          Already have a team?{" "}
          <a href="/AgentLogin" className="text-blue-600">
            Log in
          </a>
        </p>
      </div>
    </>
  );
}

export default DirectClassicSignup;
