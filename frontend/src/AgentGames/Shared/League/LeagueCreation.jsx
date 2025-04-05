import React, { useState, useEffect } from "react";
import { useSelector } from "react-redux";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { toast } from "react-toastify";

const LeagueCreation = () => {
  const token = useSelector((state) => state.auth.token);
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);

  const [games, setGames] = useState([]);
  const [leagueInfo, setLeagueInfo] = useState({
    leagueName: "",
    gameName: "",
    selectedDate: null,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [signupUrl, setSignupUrl] = useState("");

  const fetchGames = async () => {
    try {
      const response = await fetch(`${apiUrl}/user/get-available-games`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({}),
      });

      const data = await response.json();

      if (data.status === "success") {
        const gamesList = data.data.games || [];
        setGames(gamesList);

        // Set default game to first in list if available
        if (gamesList.length > 0 && !leagueInfo.gameName) {
          setLeagueInfo((prev) => ({
            ...prev,
            gameName: gamesList[0],
          }));
        }
      } else {
        setError("Failed to fetch games list");
      }
    } catch (err) {
      console.error("Error fetching games:", err);
      setError("Error connecting to server");
    }
  };

  // Fetch available games on component mount
  useEffect(() => {
    fetchGames();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setLeagueInfo((prev) => ({
      ...prev,
      [name]: value,
    }));
    setError("");
    setSignupUrl(""); // Clear previous signup URL when form changes
  };

  const handleDateChange = (date) => {
    setLeagueInfo((prev) => ({
      ...prev,
      selectedDate: date,
    }));
    setError("");
    setSignupUrl(""); // Clear previous signup URL when form changes
  };

  const validateForm = () => {
    if (!leagueInfo.leagueName.trim()) {
      setError("League name is required");
      return false;
    }

    if (!leagueInfo.gameName) {
      setError("Game selection is required");
      return false;
    }

    return true;
  };

  const handleAddLeague = async () => {
    if (!validateForm()) return;

    setIsLoading(true);

    try {
      const response = await fetch(`${apiUrl}/institution/league-create`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: leagueInfo.leagueName,
          game: leagueInfo.gameName,
          expiry_date: leagueInfo.selectedDate
            ? leagueInfo.selectedDate.toISOString()
            : undefined,
        }),
      });

      const data = await response.json();

      if (data.status === "success") {
        toast.success("League created successfully!");

        // Create the signup URL from the signup token
        if (data.data && data.data.signup_token) {
          // Using window.location to dynamically build the URL based on current domain
          const baseUrl = `${window.location.protocol}//${window.location.host}`;
          const signupPath = `/TeamSignup/${data.data.signup_token}`;
          setSignupUrl(`${baseUrl}${signupPath}`);
        }

        // Reset form after successful creation
        setLeagueInfo({
          leagueName: "",
          gameName: games[0] || "",
          selectedDate: null,
        });
      } else {
        setError(data.message || "Failed to create league");
      }
    } catch (err) {
      console.error("Error creating league:", err);
      setError("Error connecting to server");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-bold text-ui-dark mb-4">Create New League</h2>

      <div className="mb-4">
        <label htmlFor="leagueName" className="block text-ui-dark mb-1">
          League Name
        </label>
        <input
          type="text"
          id="leagueName"
          name="leagueName"
          value={leagueInfo.leagueName}
          onChange={handleChange}
          className="w-full p-2 border border-ui-light rounded"
          placeholder="Enter league name"
        />
      </div>

      <div className="mb-4">
        <label htmlFor="gameName" className="block text-ui-dark mb-1">
          Game
        </label>
        <select
          id="gameName"
          name="gameName"
          value={leagueInfo.gameName}
          onChange={handleChange}
          className="w-full p-2 border border-ui-light rounded"
        >
          <option value="" disabled>
            Select a game
          </option>
          {games.map((game, index) => (
            <option key={index} value={game}>
              {game}
            </option>
          ))}
        </select>
      </div>

      <div className="mb-4">
        <label htmlFor="expiryDate" className="block text-ui-dark mb-1">
          Expiry Date (Optional)
        </label>
        <DatePicker
          id="expiryDate"
          selected={leagueInfo.selectedDate}
          onChange={handleDateChange}
          showTimeSelect
          dateFormat="MMMM d, yyyy h:mm aa"
          className="w-full p-2 border border-ui-light rounded"
          placeholderText="Select an expiry date and time"
          minDate={new Date()}
        />
        <p className="text-sm text-ui mt-1">
          If not specified, the league will expire in 24 hours.
        </p>
      </div>

      {error && (
        <div className="mb-4 p-2 bg-danger-light text-danger rounded">
          {error}
        </div>
      )}

      <button
        onClick={handleAddLeague}
        disabled={isLoading}
        className="py-2 px-4 bg-primary hover:bg-primary-hover text-white rounded transition-colors disabled:bg-ui-light"
      >
        {isLoading ? "Creating..." : "Create League"}
      </button>

      {signupUrl && (
        <div className="mt-4 p-4 bg-success-light rounded-lg">
          <h4 className="font-medium text-success mb-2">
            League Created Successfully
          </h4>
          <p className="text-sm text-ui-dark mb-2">
            Share this link for teams to sign up directly:
          </p>
          <div className="flex items-center">
            <input
              type="text"
              value={signupUrl}
              readOnly
              className="flex-1 p-2 border border-ui-light rounded-lg text-sm bg-white"
            />
            <button
              onClick={() => {
                navigator.clipboard.writeText(signupUrl);
                toast.success("Signup URL copied to clipboard!");
              }}
              className="ml-2 p-2 bg-primary hover:bg-primary-hover text-white rounded-lg"
              title="Copy to clipboard"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
            </button>
          </div>
          <p className="mt-2 text-sm text-ui-dark">
            Teams who use this link will be directly assigned to this league
            upon signup.
          </p>
        </div>
      )}
    </div>
  );
};

export default LeagueCreation;
