// src/AgentGames/Shared/League/LeagueTeams.jsx
import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useSelector, useDispatch } from 'react-redux';
import { setTeams } from '../../../slices/teamsSlice';
import useLeagueAPI from '../hooks/useLeagueAPI';

/**
 * Shared component for managing teams in a league
 * 
 * @param {Object} props - Component props
 * @param {string} props.selected_league_name - The name of the selected league
 * @param {string} props.userRole - User role ('admin' or 'institution')
 */
const LeagueTeams = ({ selected_league_name, userRole }) => {
    const dispatch = useDispatch();
    const teams = useSelector((state) => state.teams.list);
    const apiUrl = useSelector((state) => state.settings.agentApiUrl);
    const accessToken = useSelector((state) => state.auth.token);
    
    const [filteredTeams, setFilteredTeams] = useState([]);
    const [assignTeamId, setAssignTeamId] = useState("");
    const [showAssignForm, setShowAssignForm] = useState(false);
    const [unassignedTeams, setUnassignedTeams] = useState([]);
    const [isLoadingTeams, setIsLoadingTeams] = useState(false);
    
    // Use shared API hook
    const { assignTeamToLeague, isLoading } = useLeagueAPI(userRole);

    // Fetch fresh team data when component mounts
    useEffect(() => {
        fetchAllTeams();
    }, []);

    // Filter teams when selected league or teams data changes
    useEffect(() => {
        if (!selected_league_name) return;

        // Filter teams that belong to the selected league
        const newFilteredTeams = teams.filter(
            value => value.league === selected_league_name
        );
        
        // Find teams without a league or in the "unassigned" league
        const newUnassignedTeams = teams.filter(
            value => !value.league || value.league === "unassigned"
        );
        
        setFilteredTeams(newFilteredTeams);
        setUnassignedTeams(newUnassignedTeams);
        
        if (newFilteredTeams.length === 0) {
            toast.info("No teams assigned to this league");
        }
    }, [selected_league_name, teams]);

    // Function to fetch all teams
    const fetchAllTeams = async () => {
        setIsLoadingTeams(true);
        try {
            const response = await fetch(`${apiUrl}/institution/get-all-teams`, {
                headers: {
                    'Authorization': `Bearer ${accessToken}`
                }
            });
            
            const data = await response.json();
            
            if (data.status === "success" && Array.isArray(data.data.teams)) {
                // Update Redux with fresh team data
                dispatch(setTeams(data.data.teams));
            } else if (data.status === "failed") {
                toast.error(data.message);
            }
        } catch (error) {
            console.error('Error fetching teams:', error);
        } finally {
            setIsLoadingTeams(false);
        }
    };

    const handleAssignTeam = async () => {
        if (!assignTeamId || !selected_league_name) {
            toast.error("Please select a team to assign");
            return;
        }

        // Find the league ID based on name
        const league = teams.find(team => team.league === selected_league_name)?.league_id;
        if (!league) {
            toast.error("Couldn't find league ID");
            return;
        }

        const result = await assignTeamToLeague(assignTeamId, league);
        
        if (result.success) {
            setShowAssignForm(false);
            setAssignTeamId("");
            // Refresh teams list after assignment
            fetchAllTeams();
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
                    Teams in League
                </h2>
                <div className="flex gap-2">
                    <button
                        onClick={handleRefreshTeams}
                        disabled={isLoadingTeams}
                        className="px-4 py-2 bg-primary hover:bg-primary-hover text-white text-sm rounded transition-colors"
                    >
                        {isLoadingTeams ? 'Refreshing...' : 'Refresh Teams'}
                    </button>
                    <button
                        onClick={() => setShowAssignForm(!showAssignForm)}
                        className="px-4 py-2 bg-primary hover:bg-primary-hover text-white text-sm rounded transition-colors"
                    >
                        {showAssignForm ? 'Cancel' : 'Assign Team'}
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
                            <option value="">Select a team</option>
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
                    {filteredTeams.map((team, index) => (
                        <div
                            key={index}
                            className="bg-ui-lighter p-4 rounded-lg flex items-center justify-center min-h-[60px] w-full"
                        >
                            <span className="text-base font-medium text-ui-dark break-words text-center">
                                {team.name}
                            </span>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="text-center py-4 bg-ui-lighter rounded-lg">
                    <p className="text-ui">No teams assigned to this league.</p>
                </div>
            )}
        </div>
    );
};

export default LeagueTeams;