import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useSelector } from 'react-redux';

const AdminLeagueTeams = ({ selected_league_name }) => {
    const teams = useSelector((state) => state.teams.list);
    const apiUrl = useSelector((state) => state.settings.agentApiUrl);
    const accessToken = useSelector((state) => state.auth.token);
    const [filteredTeams, setFilteredTeams] = useState([]);
    const [assignTeamId, setAssignTeamId] = useState("");
    const [showAssignForm, setShowAssignForm] = useState(false);
    const [unassignedTeams, setUnassignedTeams] = useState([]);

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
        toast.info("No teams assigned to this league");
      }
    }, [selected_league_name, teams]);

    const handleAssignTeam = () => {
      if (!assignTeamId || !selected_league_name) {
        toast.error("Please select a team to assign");
        return;
      }

      // Find the league ID based on name
      const league = teams.find(
        (team) => team.league === selected_league_name
      )?.league_id;
      if (!league) {
        toast.error("Couldn't find league ID");
        return;
      }

      // Using institution endpoint instead of admin
      fetch(`${apiUrl}/institution/assign-team-to-league`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          team_id: parseInt(assignTeamId),
          league_id: league,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "success") {
            toast.success(data.message);
            setShowAssignForm(false);
            setAssignTeamId("");
            // You would typically fetch updated teams here or update your Redux store
          } else {
            toast.error(data.message);
          }
        })
        .catch((error) => {
          toast.error("Failed to assign team to league");
        });
    };

    return (
      <div className="w-full">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-semibold text-ui-dark">
            Teams in League
          </h2>
          <button
            onClick={() => setShowAssignForm(!showAssignForm)}
            className="px-4 py-2 bg-primary hover:bg-primary-hover text-white text-sm rounded transition-colors"
          >
            {showAssignForm ? "Cancel" : "Assign Team"}
          </button>
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
                className="px-4 py-2 bg-success hover:bg-success-hover text-white rounded"
              >
                Assign
              </button>
            </div>
          </div>
        )}

        {filteredTeams.length > 0 ? (
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

export default AdminLeagueTeams;