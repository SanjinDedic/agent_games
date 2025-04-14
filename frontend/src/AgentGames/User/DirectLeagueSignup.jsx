import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useDispatch } from "react-redux";
import { setCurrentLeague, setLeagues } from '../../slices/leaguesSlice';
import useAuthAPI from "../Shared/hooks/useAuthAPI";
import useLeagueAPI from "../Shared/hooks/useLeagueAPI";

function DirectLeagueSignup() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { leagueToken } = useParams();

  // Use the authentication and league hooks
  const { directSignup, isLoading: isAuthLoading } = useAuthAPI();
  const { getLeagueInfo, isLoading: isLeagueLoading } = useLeagueAPI();

  const [leagueInfo, setLeagueInfo] = useState(null);
  const [formData, setFormData] = useState({
    teamName: "",
    password: "",
    confirmPassword: "",
    schoolName: "",
  });
  const [error, setError] = useState("");
  const isLoading = isAuthLoading || isLeagueLoading;

  // Fetch league info on load
  useEffect(() => {
    const fetchLeagueInfo = async () => {
      if (!leagueToken) return;

      const result = await getLeagueInfo(leagueToken);

      if (result.success) {
        setLeagueInfo(result.data);
      } else {
        setError("Invalid signup link or league not found");
      }
    };

    fetchLeagueInfo();
  }, [leagueToken, getLeagueInfo]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validation
    if (!formData.teamName || !formData.password) {
      setError("All fields are required");
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    // Use the direct signup hook to handle the authentication
    const result = await directSignup(
      formData.teamName,
      formData.password,
      leagueToken,
      leagueInfo,
      formData.schoolName // Add the school name parameter
    );

    if (result.success) {
      // Create a league object from the league info
      const leagueObject = {
        id: result.leagueId,
        name: leagueInfo.name,
        game: leagueInfo.game,
        created_date: leagueInfo.created_date,
        expiry_date: leagueInfo.expiry_date,
      };

      // Update Redux state with the league information
      dispatch(setLeagues([leagueObject]));
      dispatch(setCurrentLeague(leagueInfo.name));

      toast.success("Signed up and joined league successfully!");

      // Navigate to the submission page
      setTimeout(() => {
        navigate("/AgentSubmission");
      }, 300);
    } else {
      setError(result.error || "Failed to sign up");
    }
  };

  return (
    <div className="min-h-screen pt-16 flex flex-col items-center justify-center bg-ui-lighter">
      <div className="w-full max-w-md px-4">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h1 className="text-2xl font-bold text-ui-dark mb-4 text-center">
            Team Sign Up
          </h1>

          {leagueInfo ? (
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
                  <label
                    htmlFor="confirmPassword"
                    className="block text-ui-dark mb-1"
                  >
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
                  <label
                    htmlFor="schoolName"
                    className="block text-ui-dark mb-1"
                  >
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
          ) : error ? (
            <div className="text-center text-red-600 p-4">
              <p>{error}</p>
              <p className="mt-2">
                <a href="/" className="text-blue-600">
                  Return to home page
                </a>
              </p>
            </div>
          ) : (
            <div className="text-center p-4">
              <p className="text-gray-600">Loading league information...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default DirectLeagueSignup;