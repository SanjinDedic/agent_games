// src/AgentGames/Shared/League/LeagueTeams.jsx
import React, { useState, useEffect, useMemo } from "react";
import { toast } from 'react-toastify';
import { useSelector, useDispatch } from 'react-redux';
import { setTeams } from '../../../slices/teamsSlice';
import { selectToken } from '../../../slices/authSlice';
import useLeagueAPI from '../hooks/useLeagueAPI';
import { authFetch } from '../../../utils/authFetch';
import { useTerms } from '../terminology';

/**
 * Shared component for managing teams in a league
 * 
 * @param {Object} props - Component props
 * @param {string} props.selected_league_name - The name of the selected league
 * @param {string} props.userRole - User role ('admin' or 'institution')
 */
const LeagueTeams = ({ selected_league_name, userRole }) => {
    const T = useTerms();
    const dispatch = useDispatch();
    const teams = useSelector((state) => state.teams.list);
    const leagues = useSelector((state) => state.leagues.list);
    const apiUrl = useSelector((state) => state.settings.agentApiUrl);
    const accessToken = useSelector(selectToken);

    const [filteredTeams, setFilteredTeams] = useState([]);
    const [assignTeamId, setAssignTeamId] = useState("");
    const [showAssignForm, setShowAssignForm] = useState(false);
    const [unassignedTeams, setUnassignedTeams] = useState([]);
    const [isLoadingTeams, setIsLoadingTeams] = useState(false);
    const [actingTeamId, setActingTeamId] = useState(null);
    
    // Use shared API hook
  const { assignTeamToLeague, unassignTeam, isLoading } =
    useLeagueAPI(userRole);

  // Fetch fresh team data when component mounts
  useEffect(() => {
    fetchAllTeams();
  }, []);

  // Filter teams when selected league or teams data changes
  useEffect(() => {
    if (!selected_league_name) return;

    // Filter teams that belong to the selected league
    const newFilteredTeams = teams.filter(
      (value) => value.league === selected_league_name
    );

    // Find teams without a league or in the "unassigned" league
    const newUnassignedTeams = teams.filter(
      (value) => !value.league || value.league === "unassigned"
    );

    setFilteredTeams(newFilteredTeams);
    setUnassignedTeams(newUnassignedTeams);

    if (newFilteredTeams.length === 0) {
      // Only inform silently if there are absolutely no teams
      // to avoid spamming when switching leagues frequently
      // toast.info("No teams assigned to this league");
    }
  }, [selected_league_name, teams]);

  // Resolve league IDs efficiently
  const selectedLeagueId = useMemo(() => {
    const lg = leagues.find((l) => l.name === selected_league_name);
    return lg?.id;
  }, [leagues, selected_league_name]);

  // No longer rely on global 'unassigned' league discovery; the backend resolves it safely per institution

  // Function to fetch all teams
  const fetchAllTeams = async () => {
    setIsLoadingTeams(true);
    try {
      const response = await authFetch(`${apiUrl}/institution/get-all-teams`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      const data = await response.json();

      if (response.ok && Array.isArray(data.teams)) {
        // Update Redux with fresh team data
        dispatch(setTeams(data.teams));
      } else {
        toast.error(data.detail || `Failed to load ${T.teams}`);
      }
    } catch (error) {
      console.error("Error fetching teams:", error);
    } finally {
      setIsLoadingTeams(false);
    }
  };

  const handleAssignTeam = async () => {
    if (!assignTeamId || !selected_league_name) {
      toast.error(`Please select a ${T.team} to assign`);
      return;
    }

    if (!selectedLeagueId) {
      toast.error(`Couldn't find ${T.league} ID for selected ${T.league}`);
      return;
    }

    const result = await assignTeamToLeague(assignTeamId, selectedLeagueId);

    if (result.success) {
      setShowAssignForm(false);
      setAssignTeamId("");
      // Refresh teams list after assignment
      fetchAllTeams();
    }
  };

  const handleUnassignTeam = async (team) => {
    const confirm = window.confirm(
      `Move '${team.name}' to the 'unassigned' ${T.league}?`
    );
    if (!confirm) return;

    try {
      setActingTeamId(team.id);
      const result = await unassignTeam(team.id);
      if (result.success) {
        toast.success(`'${team.name}' moved to 'unassigned'`);
        fetchAllTeams();
      }
    } finally {
      setActingTeamId(null);
    }
  };

    // Button to manually refresh teams list
    const handleRefreshTeams = () => {
        fetchAllTeams();
    };

    return (
      <div className="w-full">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-semibold text-ui-dark">
            {`${T.Teams} in ${T.League}`}
          </h2>
          <div className="flex gap-2">
            <button
              onClick={handleRefreshTeams}
              disabled={isLoadingTeams}
              className="px-4 py-2 bg-primary hover:bg-primary-hover text-white text-sm rounded transition-colors"
            >
              {isLoadingTeams ? "Refreshing..." : `Refresh ${T.Teams}`}
            </button>
            <button
              onClick={() => setShowAssignForm(!showAssignForm)}
              className="px-4 py-2 bg-primary hover:bg-primary-hover text-white text-sm rounded transition-colors"
            >
              {showAssignForm ? "Cancel" : `Assign ${T.Team}`}
            </button>
          </div>
        </div>

        {showAssignForm && (
          <div className="bg-ui-lighter p-4 rounded-lg mb-6">
            <div className="flex gap-2">
              <select
                value={assignTeamId}
                onChange={(e) => setAssignTeamId(e.target.value)}
                className="flex-grow p-2 border border-ui-light rounded"
              >
                <option value="">{`Select a ${T.team}`}</option>
                {unassignedTeams.map((team) => (
                  <option key={team.id} value={team.id}>
                    {team.name}
                  </option>
                ))}
              </select>
              <button
                onClick={handleAssignTeam}
                disabled={isLoading}
                className="px-4 py-2 bg-success hover:bg-success-hover text-white rounded disabled:bg-ui-light disabled:cursor-not-allowed"
              >
                {isLoading ? "Assigning..." : "Assign"}
              </button>
            </div>
          </div>
        )}

        {isLoadingTeams ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
          </div>
        ) : filteredTeams.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {filteredTeams.map((team) => (
              <div
                key={team.id}
                className="bg-ui-lighter p-3 rounded-lg flex items-center justify-between min-h-[60px] w-full gap-2"
              >
                <span className="text-base font-medium text-ui-dark break-words">
                  {team.name}
                </span>
                <button
                  onClick={() => handleUnassignTeam(team)}
                  disabled={actingTeamId === team.id || isLoading}
                  className="px-3 py-1 text-sm rounded bg-danger text-white hover:bg-danger-hover disabled:bg-ui-light"
                  title="Move to 'unassigned'"
                >
                  {actingTeamId === team.id ? "Moving…" : "Unassign"}
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-4 bg-ui-lighter rounded-lg">
            <p className="text-ui">{`No ${T.teams} assigned to this ${T.league}.`}</p>
          </div>
        )}
      </div>
    );
};

export default LeagueTeams;