// AdminLeaguePublish.jsx
import './css/adminleague.css';
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
            feedback: currentSimulation?.feedback || null
        };

        fetch(`${apiUrl}/publish_results`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify(publishData),
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === "success") {
                    toast.success(data.message);
                } else if (data.status === "failed") {
                    toast.error(data.message);
                } else if (data.status === "error") {
                    toast.error(data.message);
                }
            })
            .catch(error => {
                toast.error(`Failed to publish results`);
            });
    };

    return (
        <button className='publish-button' onClick={handlePublish}>PUBLISH RESULT</button>
    );
}

export default AdminLeaguePublish;