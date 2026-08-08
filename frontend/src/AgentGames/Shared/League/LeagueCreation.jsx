import React, { useState, useEffect } from "react";
import { useSelector } from "react-redux";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { toast } from "react-toastify";
import { authFetch } from "../../../utils/authFetch";
import { selectToken } from '../../../slices/authSlice';
import useLeagueAPI from "../hooks/useLeagueAPI";
import { useTerms } from "../terminology";

const EMPTY_FORM = {
  leagueName: "",
  gameName: "",
  selectedDate: null,
};

/**
 * "Create New League" button that opens the creation form in a modal.
 * The form covers name, game and expiry. After a successful creation the
 * modal shows the signup link until dismissed. `compact` renders the card
 * as a single thin row (title + button) so it can share a column with
 * other cards.
 */
const LeagueCreation = ({ onCreated, compact = false }) => {
  const T = useTerms();
  const token = useSelector(selectToken);
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const { fetchUserLeagues } = useLeagueAPI();

  const [isOpen, setIsOpen] = useState(false);
  const [games, setGames] = useState([]);
  const [leagueInfo, setLeagueInfo] = useState(EMPTY_FORM);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [signupUrl, setSignupUrl] = useState("");

  const fetchGames = async () => {
    try {
      const response = await authFetch(`${apiUrl}/user/get-available-games`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({}),
      });

      const data = await response.json();

      if (response.ok) {
        const gamesList = data.games || [];
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
    const { name, value, type, checked } = e.target;
    setLeagueInfo((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
    setError("");
  };

  const handleDateChange = (date) => {
    setLeagueInfo((prev) => ({
      ...prev,
      selectedDate: date,
    }));
    setError("");
  };

  const closeModal = () => {
    setIsOpen(false);
    setError("");
    setSignupUrl("");
    setLeagueInfo({ ...EMPTY_FORM, gameName: games[0] || "" });
  };

  const validateForm = () => {
    if (!leagueInfo.leagueName.trim()) {
      setError(`${T.League} name is required`);
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
      const response = await authFetch(`${apiUrl}/admin/league-create`, {
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

      if (response.ok) {
        toast.success(`${T.League} created successfully!`);
        fetchUserLeagues();
        if (onCreated) onCreated(data);

        // Create the signup URL from the signup token
        if (data.signup_token) {
          // Using window.location to dynamically build the URL based on current domain
          const baseUrl = `${window.location.protocol}//${window.location.host}`;
          const signupPath = `/join/${data.signup_token}`;
          setSignupUrl(`${baseUrl}${signupPath}`);
        } else {
          closeModal();
        }

        // Reset form after successful creation
        setLeagueInfo({ ...EMPTY_FORM, gameName: games[0] || "" });
      } else {
        setError(data.detail || `Failed to create ${T.league}`);
      }
    } catch (err) {
      console.error("Error creating league:", err);
      setError("Error connecting to server");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={`bg-white rounded-lg shadow-lg ${compact ? 'p-4' : 'p-6'}`}>
      {compact ? (
        <div className="flex items-center justify-between gap-4">
          <h2
            className="text-lg font-bold text-ui-dark"
            title={`Set up the game and signup options for the ${T.league}.`}
          >
            {`Create New ${T.League}`}
          </h2>
          <button
            onClick={() => setIsOpen(true)}
            className="py-2 px-4 bg-primary hover:bg-primary-hover text-white rounded transition-colors whitespace-nowrap"
          >
            {`Create ${T.League}`}
          </button>
        </div>
      ) : (
        <>
          <h2 className="text-xl font-bold text-ui-dark mb-4">{`Create New ${T.League}`}</h2>
          <p className="text-sm text-ui mb-4">
            {`Set up the game and signup options for the ${T.league}.`}
          </p>
          <button
            onClick={() => setIsOpen(true)}
            className="w-full py-2 px-4 bg-primary hover:bg-primary-hover text-white rounded transition-colors"
          >
            {`Create ${T.League}`}
          </button>
        </>
      )}

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-ui-dark">
                {`Create New ${T.League}`}
              </h2>
              <button
                onClick={closeModal}
                className="text-ui-dark/60 hover:text-ui-dark text-2xl leading-none"
                aria-label="Close"
              >
                &times;
              </button>
            </div>

            {signupUrl ? (
              <div className="p-4 bg-success-light rounded-lg">
                <h4 className="font-medium text-success mb-2">
                  {`${T.League} Created Successfully`}
                </h4>
                <p className="text-sm text-ui-dark mb-2">
                  {`This is the ${T.league}'s login page — ${T.teams} use it to sign up and log in:`}
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
                  {`${T.Teams} who use this link will be directly assigned to this ${T.league} upon signup.`}
                </p>
                <button
                  onClick={closeModal}
                  className="mt-4 w-full py-2 px-4 bg-primary hover:bg-primary-hover text-white rounded transition-colors"
                >
                  Done
                </button>
              </div>
            ) : (
              <>
                <div className="mb-4">
                  <label htmlFor="leagueName" className="block text-ui-dark mb-1">
                    {`${T.League} Name`}
                  </label>
                  <input
                    type="text"
                    id="leagueName"
                    name="leagueName"
                    value={leagueInfo.leagueName}
                    onChange={handleChange}
                    className="w-full p-2 border border-ui-light rounded"
                    placeholder={`Enter ${T.league} name`}
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
                    {`If not specified, the ${T.league} will expire in 24 hours.`}
                  </p>
                </div>

                {error && (
                  <div className="mb-4 p-2 bg-danger-light text-danger rounded">
                    {error}
                  </div>
                )}

                <div className="flex gap-2">
                  <button
                    onClick={handleAddLeague}
                    disabled={isLoading}
                    className="flex-1 py-2 px-4 bg-primary hover:bg-primary-hover text-white rounded transition-colors disabled:bg-ui-light"
                  >
                    {isLoading ? "Creating..." : `Create ${T.League}`}
                  </button>
                  <button
                    onClick={closeModal}
                    className="py-2 px-4 bg-ui-light hover:bg-ui-light/80 text-ui-dark rounded transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default LeagueCreation;
