import React, { useState, useEffect } from "react";
import { useSelector } from "react-redux";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { toast } from "react-toastify";
import { authFetch } from "../../../utils/authFetch";

const LeagueCreation = () => {
  const token = useSelector((state) => state.auth.token);
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);

  const [games, setGames] = useState([]);
  const [leagueInfo, setLeagueInfo] = useState({
    leagueName: "",
    gameName: "",
    selectedDate: null,
    schoolLeague: false,
    schoolsSource: "static",
    schoolsText: "",
    sheetUrl: "",
  });
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
    const { name, value, type, checked } = e.target;
    setLeagueInfo((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
    setError("");
    setSignupUrl(""); // Clear previous signup URL when form changes
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
          setCreatedSchoolLeague(Boolean(data.data.school_league));
        }

        // Reset form after successful creation
        setLeagueInfo({
          leagueName: "",
          gameName: games[0] || "",
          selectedDate: null,
          schoolLeague: false,
          schoolsSource: "static",
          schoolsText: "",
          sheetUrl: "",
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
          School league (students pick their school from a dropdown; team names
          auto-generated; no email, no password recovery)
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
              <label htmlFor="schoolsText" className="block text-ui-dark mb-1">
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
                Students will pick from this list at signup. At least one
                school is required.
              </p>
            </>
          ) : (
            <>
              <label htmlFor="sheetUrl" className="block text-ui-dark mb-1">
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
                Share the sheet as <strong>Anyone with the link &mdash; Viewer</strong>.
                Put school names in column A; the first row is treated as a
                header. The list refreshes automatically every 5 minutes.
              </p>
            </>
          )}

          <p className="text-sm text-ui mt-3">
            Remind students to save their passwords &mdash; there is no
            recovery.
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
          {createdSchoolLeague && (
            <p className="mt-2 text-sm text-danger font-medium">
              School league: tell students to save their passwords. There is no
              recovery &mdash; if they lose it they will need to sign up again
              under a new team number.
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default LeagueCreation;
