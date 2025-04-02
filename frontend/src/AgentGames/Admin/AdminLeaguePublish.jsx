import React from 'react';
import { toast } from 'react-toastify';
import { useSelector } from 'react-redux';

const AdminLeaguePublish = ({ simulation_id, selected_league_name }) => {
    const apiUrl = useSelector((state) => state.settings.agentApiUrl);
    const accessToken = useSelector((state) => state.auth.token);
    const currentSimulation = useSelector((state) => state.leagues.currentLeagueResultSelected);

    const handlePublish = () => {
      if (simulation_id === "" || !selected_league_name) {
        toast.error(`Please select a league`);
        return;
      }

      const publishData = {
        league_name: selected_league_name,
        id: simulation_id,
        feedback: currentSimulation?.feedback || null,
      };

      // Important: Now using the institution endpoint instead of admin
      fetch(`${apiUrl}/institution/publish-results`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(publishData),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "success") {
            toast.success(data.message);
          } else if (data.status === "failed" || data.status === "error") {
            toast.error(data.message);
          }
        })
        .catch((error) => {
          toast.error(`Failed to publish results`);
        });
    };

    return (
        <button
            onClick={handlePublish}
            className="w-full bg-success hover:bg-success-hover text-white py-3 px-4 rounded-lg text-lg font-medium transition-colors shadow-sm focus:ring-2 focus:ring-success focus:ring-offset-2 outline-none"
        >
            PUBLISH RESULT
        </button>
    );
}

export default AdminLeaguePublish;