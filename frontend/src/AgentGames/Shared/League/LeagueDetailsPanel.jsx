// src/AgentGames/Shared/League/LeagueDetailsPanel.jsx
import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useSelector, useDispatch } from 'react-redux';
import moment from 'moment-timezone';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import Editor from '@monaco-editor/react';

// Import Redux actions
import { updateExpiryDate } from "../../../slices/leaguesSlice";
import { selectToken } from '../../../slices/authSlice';
import { authFetch } from '../../../utils/authFetch';

// Import shared components
import LeagueTeams from './LeagueTeams';
import PureMarkdown from '../Utilities/PureMarkdown';
import StatChip from '../Common/StatChip';
import useLeagueAPI from '../hooks/useLeagueAPI';
import { useTerms } from '../terminology';

// Mirrors StatChip's tones so the inline expiry editor reads as one of the chips.
const EXPIRY_TONES = {
  plain: 'bg-ui-lighter border-ui-light text-ui-dark',
  warning: 'bg-notice-orange/10 border-notice-orange/40 text-ui-dark',
  danger: 'bg-danger-light border-danger/30 text-danger',
};

/**
 * The details card for the league currently selected in Redux: expiry,
 * shareable login page, markdown info editor, delete.
 * `showTeams` adds the assign/unassign grid (the admin management
 * page wants it; the classroom workspace's Students tab owns membership).
 * `onDeleted` fires after a successful delete so the caller can navigate.
 */
const LeagueDetailsPanel = ({ showTeams = true, onDeleted }) => {
  const T = useTerms();
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const accessToken = useSelector(selectToken);
  const currentLeague = useSelector((state) => state.leagues.currentLeague);

  const [signupLink, setSignupLink] = useState("");
  const [showSignupLink, setShowSignupLink] = useState(false);
  const [isLoadingSignupLink, setIsLoadingSignupLink] = useState(false);

  // Use the shared API hook
  const {
    updateExpiryDate: updateLeagueExpiry,
    updateLeagueInfo,
    deleteLeague,
  } = useLeagueAPI();

  const [infoMarkdownDraft, setInfoMarkdownDraft] = useState('');
  const [isSavingInfo, setIsSavingInfo] = useState(false);
  const [showInfoPreview, setShowInfoPreview] = useState(false);
  const [showInfoEditor, setShowInfoEditor] = useState(false);
  // Roster count for the overview chip, from the loaded teams list.
  const allTeams = useSelector((state) => state.teams.list);

  moment.tz.setDefault("Australia/Sydney");

  // Reset markdown draft when the selected league changes
  useEffect(() => {
    setInfoMarkdownDraft(currentLeague?.info_markdown ?? '');
    setShowInfoPreview(false);
  }, [currentLeague?.id, currentLeague?.info_markdown]);

  // Check for existing signup links when currentLeague changes
  useEffect(() => {
    if (currentLeague && currentLeague.signup_link) {
      const baseUrl = `${window.location.protocol}//${window.location.host}`;
      const signupPath = `/join/${currentLeague.signup_link}`;
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
        `${apiUrl}/admin/generate-signup-link`,
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
        const signupPath = `/join/${data.signup_token}`;
        const fullUrl = `${baseUrl}${signupPath}`;

        setSignupLink(fullUrl);
        setShowSignupLink(true);

        toast.success(`Login page created for ${leagueName}`);
      } else {
        toast.error(data.detail || "Failed to generate the login page link");
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

    const result = await deleteLeague(currentLeague.id);
    if (result.success && onDeleted) {
      onDeleted();
    }
  };

  // Handle expiry date update.
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

  // Copy signup link to clipboard
  const copySignupLink = () => {
    navigator.clipboard.writeText(signupLink);
    toast.success("Login page link copied to clipboard!");
  };

  const isActive =
    currentLeague != null &&
    moment().isBefore(moment(currentLeague.expiry_date));
  // Amber inside a week, red once expired.
  const daysLeft = currentLeague
    ? moment(currentLeague.expiry_date).diff(moment(), 'days')
    : 0;
  const expiryTone = !isActive ? 'danger' : daysLeft < 7 ? 'warning' : 'plain';
  const teamCount = currentLeague
    ? allTeams.filter((team) => team.league === currentLeague.name).length
    : 0;

  if (!currentLeague) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6 flex items-center justify-center">
        <p className="text-ui-dark text-lg">
          {`Select a ${T.league} from the list or create a new one to get started.`}
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold text-ui-dark mb-6">
        {`${T.League} Details`}
      </h2>

      {/* Overview — the expiry chip is the editor, no separate section */}
      <div className="mb-6">
        <div className="flex flex-wrap gap-3">
          <StatChip label="Game" value={currentLeague.game} />
          <StatChip
            label="Status"
            value={isActive ? 'Active' : 'Expired'}
            tone={isActive ? 'success' : 'danger'}
          />
          <StatChip
            label={T.Teams}
            value={teamCount}
            title={`${T.Teams} enrolled in this ${T.league}`}
          />
          <StatChip
            label="Created"
            value={moment(currentLeague.created_date).format('D MMM YYYY')}
          />
          <div
            className={`px-4 py-2 rounded-lg border ${EXPIRY_TONES[expiryTone]}`}
            title="Click the date to change it"
          >
            <div className="text-xs uppercase tracking-wide text-ui">
              {isActive ? 'Expires' : 'Expired'}
            </div>
            <div className="flex items-baseline gap-2">
              <DatePicker
                selected={new Date(currentLeague.expiry_date)}
                onChange={handleExpiryDateChange}
                showTimeSelect
                dateFormat="d MMM yyyy, h:mm aa"
                className="w-44 bg-transparent text-base font-semibold leading-tight cursor-pointer outline-none border-b border-dashed border-ui"
              />
              <span className="text-sm">
                {moment(currentLeague.expiry_date).fromNow()}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Shareable login page — one slim row, the URL is the content */}
      <div className="mb-6">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-ui-dark whitespace-nowrap">
            Login page
          </span>
          {showSignupLink ? (
            <>
              <input
                type="text"
                value={signupLink}
                readOnly
                className="flex-1 min-w-64 p-2 border border-ui-light rounded-lg text-sm bg-ui-lighter"
              />
              <button
                onClick={copySignupLink}
                className="p-2 bg-primary hover:bg-primary-hover text-white rounded-lg"
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
            </>
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
                : `Create ${T.League} Login Page`}
            </button>
          )}
        </div>
        {showSignupLink && (
          <p className="text-xs text-ui mt-1">
            {`Share this page with your ${T.teams} — they use it to sign up and log in to this ${T.league}.`}
          </p>
        )}
      </div>

      {/* League Info Markdown — rendered by default, editor on demand */}
      <div className="mb-6 border-t border-ui-light pt-5">
        <div className="flex flex-wrap justify-between items-center gap-2 mb-2">
          <h3 className="text-lg font-medium text-ui-dark">
            {`${T.League} Info`}
          </h3>
          <div className="flex items-center gap-2">
            {showInfoEditor && (
              <>
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
              </>
            )}
            <button
              type="button"
              onClick={() => setShowInfoEditor((v) => !v)}
              className="px-3 py-1 text-sm bg-ui-light hover:bg-ui-light/80 text-ui-dark rounded"
            >
              {showInfoEditor ? 'Done' : 'Edit Markdown'}
            </button>
          </div>
        </div>
        <p className="text-sm text-ui mb-3">
          {`Shown to ${T.teams} enrolled in this ${T.league} on the leaderboard page. Use it for the simulation schedule, publishing cadence, ${T.league} rules, etc.`}
        </p>

        {showInfoEditor ? (
          <div className={showInfoPreview ? 'grid grid-cols-1 md:grid-cols-2 gap-4' : ''}>
            <div className="border border-ui-light rounded overflow-hidden" style={{ height: '240px' }}>
              <Editor
                height="240px"
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
              <div className="border border-ui-light rounded p-3 bg-ui-lighter overflow-auto" style={{ height: '240px' }}>
                {infoMarkdownDraft.trim() ? (
                  <PureMarkdown content={infoMarkdownDraft} />
                ) : (
                  <p className="text-ui">Nothing to preview yet.</p>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="border border-ui-light rounded p-3 bg-ui-lighter overflow-auto max-h-60">
            {(currentLeague.info_markdown ?? '').trim() ? (
              <PureMarkdown content={currentLeague.info_markdown} />
            ) : (
              <p className="text-ui">
                {`Nothing here yet — Edit Markdown to write a welcome note for your ${T.teams}.`}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Teams Grid */}
      {showTeams && (
        <LeagueTeams
          selected_league_name={currentLeague.name}
        />
      )}

      {/* Danger zone — the destructive action lives last, away from daily controls */}
      <div className="border-t border-ui-light pt-5 mt-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-medium text-ui-dark">Danger zone</h3>
            <p className="text-sm text-ui">
              {`Deleting this ${T.league} moves all its ${T.teams} to the unassigned ${T.league}.`}
            </p>
          </div>
          <button
            onClick={handleDeleteLeague}
            className="px-4 py-2 bg-danger hover:bg-danger-hover text-white rounded-lg transition-colors disabled:bg-ui-light disabled:cursor-not-allowed"
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
      </div>
    </div>
  );
};

export default LeagueDetailsPanel;
