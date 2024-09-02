import './css/adminleague.css';
import React from 'react';
import { toast } from 'react-toastify';
import { useSelector } from 'react-redux';


const AdminLeaguePublish = ({ simulation_id, selected_league_name }) => {
    const apiUrl = useSelector((state) => state.settings.agentApiUrl);
    const accessToken = useSelector((state) => state.auth.token);

    const handlePublish = () => {
        if (simulation_id === "" || !selected_league_name) {
            toast.error(`Please select a league`);
            return;
        }

        fetch(`${apiUrl}/publish_results`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({ league_name: selected_league_name, id: simulation_id }),
        })
            .then(response => response.json())
            .then(data => {

                if (data.status === "success") {
                    toast.success(data.message);
                } else if (data.status === "failed") {
                    toast.error(data.message);
                } else if (data.status === "error") {
                    toast.error(data.message);
                    return;
                }
            })
            .catch(error => {

                toast.error(`Failed to add League`);
            });
    };
    return (
        <button className='publish-button' onClick={handlePublish}>PUBLISH RESULT</button>
    );
}
export default AdminLeaguePublish;