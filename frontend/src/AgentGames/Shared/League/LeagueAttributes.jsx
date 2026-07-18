// src/AgentGames/Shared/League/LeagueAttributes.jsx
import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useSelector, useDispatch } from 'react-redux';
import moment from 'moment-timezone';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { useNavigate } from 'react-router-dom';
import Editor from '@monaco-editor/react';

// Import Redux actions
import { updateExpiryDate } from "../../../slices/leaguesSlice";
import { selectToken } from '../../../slices/authSlice';
import { authFetch } from '../../../utils/authFetch';

// Import shared components
import LeagueTeams from './LeagueTeams';
import LeagueCreation from './LeagueCreation';
import LeagueTutorials from './LeagueTutorials';
import LeagueCardList from "./LeagueCardList";
import PureMarkdown from '../Utilities/PureMarkdown';
import useLeagueAPI from '../hooks/useLeagueAPI';
import { useTerms } from '../terminology';

const LeagueAttributes = ({ userRole, redirectPath, onUnauthorized }) => {
  const T = useTerms();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);
  const currentLeague = useSelector((state) => state.leagues.currentLeague);

  const [signupLink, setSignupLink] = useState("");
  const [showSignupLink, setShowSignupLink] = useState(false);
  const [isLoadingSignupLink, setIsLoadingSignupLink] = useState(false);

  // Use the shared API hook
  const {
    fetchUserLeagues,
    updateExpiryDate: updateLeagueExpiry,
    updateLeagueInfo,
    deleteLeague,
    isLoading,
  } = useLeagueAPI(userRole);

  const [infoMarkdownDraft, setInfoMarkdownDraft] = useState('');
  const [isSavingInfo, setIsSavingInfo] = useState(false);
  const [showInfoPreview, setShowInfoPreview] = useState(false);

  moment.tz.setDefault("Australia/Sydney");

  useEffect(() => {
    fetchUserLeagues();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reset markdown draft when the selected league changes
  useEffect(() => {
    setInfoMarkdownDraft(currentLeague?.info_markdown ?? '');
    setShowInfoPreview(false);
  }, [currentLeague?.id, currentLeague?.info_markdown]);

  // Check for existing signup links when currentLeague changes
  useEffect(() => {
    if (currentLeague && currentLeague.signup_link) {
      const baseUrl = `${window.location.protocol}//${window.location.host}`;
      const signupPath = `/TeamSignup/${currentLeague.signup_link}`;
      setSignupLink(`${baseUrl}${signupPath}`);
      setShowSignupLink(true);
    } else {
      setShowSignupLink(false);
      setSignupLink("");
    }
  }, [currentLeague]);

  // Generate signup link for a league
  const generateSignupLink = async (leagueId, leagueName) => {
    if (!leagueId) return;

    setIsLoadingSignupLink(true);
    try {
      const response = await authFetch(
        `${apiUrl}/institution/generate-signup-link`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({ league_id: leagueId }),
        }
      );

      const data = await response.json();

      if (response.ok && data.signup_token) {
        const baseUrl = `${window.location.protocol}//${window.location.host}`;
        const signupPath = `/TeamSignup/${data.signup_token}`;
        const fullUrl = `${baseUrl}${signupPath}`;

        setSignupLink(fullUrl);
        setShowSignupLink(true);

        toast.success(`Signup link generated for ${leagueName}`);
      } else {
        toast.error(data.detail || "Failed to generate signup link");
      }
    } catch (error) {
      console.error("Error generating signup link:", error);
      toast.error("Network error while generating signup link");
    } finally {
      setIsLoadingSignupLink(false);
    }
  };

  // Handle league deletion
  const handleDeleteLeague = async () => {
    if (!currentLeague) return;

    if (currentLeague.name.toLowerCase() === "unassigned") {
      toast.error(`Cannot delete the 'unassigned' ${T.league}`);
      return;
    }

    if (
      !window.confirm(
        `Are you sure you want to delete ${T.league} "${currentLeague.name}"? All ${T.teams} will be moved to the unassigned ${T.league}.`
      )
    ) {
      return;
    }

    await deleteLeague(currentLeague.id);
  };

  // Handle expiry date update
  const handleExpiryDateChange = async (date) => {
    const formattedDate = date.toISOString();
    
    try {
      const result = await updateLeagueExpiry(currentLeague.id, formattedDate);
      
      if (result.success) {
        dispatch(updateExpiryDate({ 
          name: currentLeague.name, 
          expiry_date: formattedDate 
        }));
      }
    } catch (error) {
      console.error('Error updating date:', error);
    }
  };

  // Save markdown info for the selected league
  const handleSaveInfo = async () => {
    if (!currentLeague) return;
    setIsSavingInfo(true);
    try {
      await updateLeagueInfo(currentLeague.id, infoMarkdownDraft);
    } finally {
      setIsSavingInfo(false);
    }
  };

  const infoHasChanges =
    currentLeague != null &&
    (currentLeague.info_markdown ?? '') !== infoMarkdownDraft;

  // Navigate to the simulation page
  const handleGoToSimulation = () => {
    const path = userRole === 'admin' ? '/AdminLeagueSimulation' : '/InstitutionLeagueSimulation';
    navigate(path);
  };
  
  // Copy signup link to clipboard
  const copySignupLink = () => {
    navigator.clipboard.writeText(signupLink);
    toast.success("Signup link copied to clipboard!");
  };

  return (
    <div className="min-h-screen bg-ui-lighter">
      <div className="max-w-[1800px] mx-auto px-6 pt-20 pb-8">
        {/* Header section */}
        <div className="mb-6">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-ui-dark mb-4">
              {`${T.League} Management`}
            </h1>
            <button
              onClick={handleGoToSimulation}
              className="px-4 py-2 bg-notice-orange hover:bg-notice-orange/90 text-white rounded-lg transition-colors"
            >
              Go to Simulation & Results
            </button>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left Column - League List (1/4 width) */}
          <div className="space-y-4">
            <div className="bg-white rounded-lg shadow-lg p-4">
              <h2 className="text-xl font-semibold text-ui-dark mb-4">
                {T.Leagues}
              </h2>
              <LeagueCardList userRole={userRole} />
            </div>

            {/* League Creation */}
            <LeagueCreation userRole={userRole} />
          </div>

          {/* Right Column - League Details (3/4 width) */}
          <div className="lg:col-span-3 space-y-6">
            {/* League Attributes Card */}
            {currentLeague ? (
              <div className="bg-white rounded-lg shadow-lg p-6">
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-xl font-semibold text-ui-dark">
                    {`${T.League} Details`}
                  </h2>
                  <button
                    onClick={handleDeleteLeague}
                    className="px-4 py-2 bg-danger hover:bg-danger-hover text-white rounded-lg transition-colors"
                    disabled={currentLeague.name.toLowerCase() === "unassigned"}
                    title={
                      currentLeague.name.toLowerCase() === "unassigned"
                        ? `Cannot delete the unassigned ${T.league}`
                        : `Delete this ${T.league}`
                    }
                  >
                    {`Delete ${T.League}`}
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  <div>
                    <span className="block text-ui">{`${T.League} Name:`}</span>
                    <span className="block text-lg font-medium text-ui-dark">
                      {currentLeague.name}
                    </span>
                  </div>

                  <div>
                    <span className="block text-ui">Game Type:</span>
                    <span className="block text-lg font-medium text-ui-dark">
                      {currentLeague.game}
                    </span>
                  </div>

                  <div>
                    <span className="block text-ui">Created Date:</span>
                    <span className="block text-lg font-medium text-ui-dark">
                      {moment(currentLeague.created_date).format(
                        "MMMM D, YYYY"
                      )}
                    </span>
                  </div>

                  <div>
                    <span className="block text-ui">Status:</span>
                    <span
                      className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                        moment().isBefore(moment(currentLeague.expiry_date))
                          ? "bg-success-light text-success"
                          : "bg-danger-light text-danger"
                      }`}
                    >
                      {moment().isBefore(moment(currentLeague.expiry_date))
                        ? "Active"
                        : "Expired"}
                    </span>
                  </div>
                </div>

                {/* League Expiry Date Editor */}
                <div className="mb-6">
                  <h3 className="text-lg font-medium text-ui-dark mb-2">
                    {`${T.League} Expiry`}
                  </h3>
                  <div className="flex items-center gap-2">
                    <DatePicker
                      selected={new Date(currentLeague.expiry_date)}
                      onChange={handleExpiryDateChange}
                      showTimeSelect
                      dateFormat="MMMM d, yyyy h:mm aa"
                      className="p-2 border border-ui-light rounded w-64"
                    />
                    <span className="text-ui">
                      {moment(currentLeague.expiry_date).fromNow()}
                    </span>
                  </div>
                </div>

                {/* League Signup Link */}
                <div className="mb-6">
                  <h3 className="text-lg font-medium text-ui-dark mb-2">
                    Signup Link
                  </h3>

                  {showSignupLink ? (
                    <div className="p-4 bg-success-light rounded-lg">
                      <div className="flex items-center">
                        <input
                          type="text"
                          value={signupLink}
                          readOnly
                          className="flex-1 p-2 border border-ui-light rounded-lg text-sm bg-white"
                        />
                        <button
                          onClick={copySignupLink}
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
                        {`Share this link for ${T.teams} to sign up directly to this ${T.league}.`}
                      </p>
                    </div>
                  ) : (
                    <button
                      onClick={() =>
                        generateSignupLink(currentLeague.id, currentLeague.name)
                      }
                      disabled={isLoadingSignupLink}
                      className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg transition-colors disabled:bg-ui-light disabled:cursor-not-allowed"
                    >
                      {isLoadingSignupLink
                        ? "Generating..."
                        : "Generate Signup Link"}
                    </button>
                  )}
                </div>

                {/* League Info Markdown */}
                <div className="mb-6">
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="text-lg font-medium text-ui-dark">
                      {`${T.League} Info (Markdown)`}
                    </h3>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setShowInfoPreview((v) => !v)}
                        className="px-3 py-1 text-sm bg-ui-light hover:bg-ui-light/80 text-ui-dark rounded"
                      >
                        {showInfoPreview ? 'Hide Preview' : 'Show Preview'}
                      </button>
                      <button
                        type="button"
                        onClick={handleSaveInfo}
                        disabled={!infoHasChanges || isSavingInfo}
                        className="px-3 py-1 text-sm bg-primary hover:bg-primary-hover text-white rounded disabled:bg-ui-light disabled:cursor-not-allowed"
                      >
                        {isSavingInfo ? 'Saving...' : 'Save Info'}
                      </button>
                    </div>
                  </div>
                  <p className="text-sm text-ui mb-2">
                    {`Shown to ${T.teams} enrolled in this ${T.league} on the leaderboard page. Use it for the simulation schedule, publishing cadence, ${T.league} rules, etc.`}
                  </p>
                  <div className={showInfoPreview ? 'grid grid-cols-1 md:grid-cols-2 gap-4' : ''}>
                    <div className="border border-ui-light rounded overflow-hidden" style={{ height: '320px' }}>
                      <Editor
                        height="320px"
                        defaultLanguage="markdown"
                        language="markdown"
                        theme="vs-dark"
                        value={infoMarkdownDraft}
                        onChange={(value) => setInfoMarkdownDraft(value ?? '')}
                        options={{
                          minimap: { enabled: false },
                          wordWrap: 'on',
                          fontSize: 14,
                          lineNumbers: 'on',
                          automaticLayout: true,
                          scrollBeyondLastLine: false,
                        }}
                      />
                    </div>
                    {showInfoPreview && (
                      <div className="border border-ui-light rounded p-3 bg-ui-lighter overflow-auto" style={{ height: '320px' }}>
                        {infoMarkdownDraft.trim() ? (
                          <PureMarkdown content={infoMarkdownDraft} />
                        ) : (
                          <p className="text-ui">Nothing to preview yet.</p>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* League Tutorials */}
                <LeagueTutorials
                  leagueId={currentLeague.id}
                  userRole={userRole}
                />

                {/* Teams Grid */}
                <LeagueTeams
                  selected_league_name={currentLeague.name}
                  userRole={userRole}
                />
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-lg p-6 flex items-center justify-center">
                <p className="text-ui-dark text-lg">
                  {`Select a ${T.league} from the list or create a new one to get started.`}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LeagueAttributes;