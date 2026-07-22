import React, { useState, useEffect } from "react";
import { useSelector } from "react-redux";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { toast } from "react-toastify";
import { authFetch } from "../../../utils/authFetch";
import { selectToken } from '../../../slices/authSlice';
import LeagueTutorialSelector from "./LeagueTutorialSelector";
import useLeagueAPI from "../hooks/useLeagueAPI";
import { useTerms } from "../terminology";

const EMPTY_FORM = {
  leagueName: "",
  gameName: "",
  selectedDate: null,
  schoolLeague: false,
  schoolsSource: "static",
  schoolsText: "",
  sheetUrl: "",
  tutorialIds: [],
};

/**
 * "Create New League" button that opens the creation form in a modal.
 * The form covers name, game, school-league settings, expiry, and which
 * tutorials the league's teams will see. After a successful creation the
 * modal shows the signup link until dismissed.
 */
const LeagueCreation = ({ userRole, onCreated }) => {
  const T = useTerms();
  const token = useSelector(selectToken);
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const { fetchUserLeagues } = useLeagueAPI(userRole);

  const [isOpen, setIsOpen] = useState(false);
  const [games, setGames] = useState([]);
  const [leagueInfo, setLeagueInfo] = useState(EMPTY_FORM);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [signupUrl, setSignupUrl] = useState("");
  const [createdSchoolLeague, setCreatedSchoolLeague] = useState(false);

  const SHEETS_URL_RE = /\/spreadsheets\/d\/[a-zA-Z0-9_-]+/;

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

  const handleTutorialsChange = (tutorialIds) => {
    setLeagueInfo((prev) => ({ ...prev, tutorialIds }));
    setError("");
  };

  const parseSchools = (text) =>
    text
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);

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
    setCreatedSchoolLeague(false);
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

    if (leagueInfo.schoolLeague) {
      if (leagueInfo.schoolsSource === "sheet") {
        const url = leagueInfo.sheetUrl.trim();
        if (!url) {
          setError("Enter a Google Sheet URL");
          return false;
        }
        if (!SHEETS_URL_RE.test(url)) {
          setError(
            "That doesn't look like a Google Sheets URL (expected /spreadsheets/d/...)."
          );
          return false;
        }
      } else {
        const schools = parseSchools(leagueInfo.schoolsText);
        if (schools.length === 0) {
          setError("Add at least one school (one per line)");
          return false;
        }
      }
    }

    return true;
  };

  const handleAddLeague = async () => {
    if (!validateForm()) return;

    setIsLoading(true);

    try {
      const response = await authFetch(`${apiUrl}/institution/league-create`, {
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
          school_league: leagueInfo.schoolLeague,
          schools:
            leagueInfo.schoolLeague && leagueInfo.schoolsSource === "static"
              ? parseSchools(leagueInfo.schoolsText)
              : [],
          sheet_url:
            leagueInfo.schoolLeague && leagueInfo.schoolsSource === "sheet"
              ? leagueInfo.sheetUrl.trim()
              : null,
          tutorial_ids: leagueInfo.tutorialIds,
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
          setCreatedSchoolLeague(Boolean(data.school_league));
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
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-bold text-ui-dark mb-4">{`Create New ${T.League}`}</h2>
      <p className="text-sm text-ui mb-4">
        {`Set up the game, signup options, and the ${T.tutorials} ${T.teams} in the ${T.league} will see.`}
      </p>
      <button
        onClick={() => setIsOpen(true)}
        className="w-full py-2 px-4 bg-primary hover:bg-primary-hover text-white rounded transition-colors"
      >
        {`Create ${T.League}`}
      </button>

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
                {createdSchoolLeague && (
                  <p className="mt-2 text-sm text-danger font-medium">
                    {`School ${T.league}: tell students to save their passwords. There is no recovery — if they lose it they will need to sign up again under a new ${T.team} number.`}
                  </p>
                )}
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
                  <label className="block text-ui-dark mb-1">{T.Tutorials}</label>
                  <p className="text-sm text-ui mb-2">
                    {`${T.Teams} in this ${T.league} will only see the ${T.tutorials} selected here. Leave empty for no ${T.tutorials}.`}
                  </p>
                  <LeagueTutorialSelector
                    selectedIds={leagueInfo.tutorialIds}
                    onChange={handleTutorialsChange}
                  />
                </div>

                <div className="mb-4 flex items-center">
                  <input
                    type="checkbox"
                    id="schoolLeague"
                    name="schoolLeague"
                    checked={leagueInfo.schoolLeague}
                    onChange={handleChange}
                    className="mr-2"
                  />
                  <label htmlFor="schoolLeague" className="text-ui-dark">
                    {`School ${T.league} (students pick their school from a dropdown; ${T.team} names auto-generated; no email, no password recovery)`}
                  </label>
                </div>

                {leagueInfo.schoolLeague && (
                  <div className="mb-4 border border-ui-light rounded p-3">
                    <div className="mb-3 flex gap-4">
                      <label className="flex items-center">
                        <input
                          type="radio"
                          name="schoolsSource"
                          value="static"
                          checked={leagueInfo.schoolsSource === "static"}
                          onChange={handleChange}
                          className="mr-2"
                        />
                        Paste list
                      </label>
                      <label className="flex items-center">
                        <input
                          type="radio"
                          name="schoolsSource"
                          value="sheet"
                          checked={leagueInfo.schoolsSource === "sheet"}
                          onChange={handleChange}
                          className="mr-2"
                        />
                        Google Sheet URL
                      </label>
                    </div>

                    {leagueInfo.schoolsSource === "static" ? (
                      <>
                        <label
                          htmlFor="schoolsText"
                          className="block text-ui-dark mb-1"
                        >
                          Schools (one per line)
                        </label>
                        <textarea
                          id="schoolsText"
                          name="schoolsText"
                          rows={6}
                          value={leagueInfo.schoolsText}
                          onChange={handleChange}
                          className="w-full p-2 border border-ui-light rounded font-mono text-sm"
                          placeholder={"Willetton SHS\nPerth Modern\nApplecross SHS"}
                        />
                        <p className="text-sm text-ui mt-1">
                          Students will pick from this list at signup. At least
                          one school is required.
                        </p>
                      </>
                    ) : (
                      <>
                        <label
                          htmlFor="sheetUrl"
                          className="block text-ui-dark mb-1"
                        >
                          Google Sheet URL
                        </label>
                        <input
                          id="sheetUrl"
                          name="sheetUrl"
                          type="text"
                          value={leagueInfo.sheetUrl}
                          onChange={handleChange}
                          className="w-full p-2 border border-ui-light rounded font-mono text-sm"
                          placeholder="https://docs.google.com/spreadsheets/d/..."
                        />
                        <p className="text-sm text-ui mt-1">
                          Share the sheet as{" "}
                          <strong>Anyone with the link &mdash; Viewer</strong>.
                          Put school names in column A; the first row is treated
                          as a header. The list refreshes automatically every 5
                          minutes.
                        </p>
                      </>
                    )}

                    <p className="text-sm text-ui mt-3">
                      Remind students to save their passwords &mdash; there is
                      no recovery.
                    </p>
                  </div>
                )}

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
