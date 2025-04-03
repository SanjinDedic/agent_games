// src/AgentGames/Shared/League/LeaguePublish.jsx
import React from 'react';
import { useSelector } from 'react-redux';
import useLeagueAPI from '../hooks/useLeagueAPI';

/**
 * Shared component for publishing league results
 * 
 * @param {Object} props - Component props
 * @param {string} props.simulation_id - ID of the simulation to publish
 * @param {string} props.selected_league_name - Name of the selected league
 * @param {string} props.userRole - User role ('admin' or 'institution')
 */
const LeaguePublish = ({ simulation_id, selected_league_name, userRole }) => {
    const currentSimulation = useSelector((state) => state.leagues.currentLeagueResultSelected);
    
    // Use the shared API hook
    const { publishResults, isLoading } = useLeagueAPI(userRole);

    const handlePublish = async () => {
        if (!simulation_id || !selected_league_name) {
            return;
        }

        const publishData = {
            league_name: selected_league_name,
            id: simulation_id,
            feedback: currentSimulation?.feedback || null
        };

        await publishResults(publishData);
    };

    return (
        <button
            onClick={handlePublish}
            disabled={isLoading || !simulation_id || !selected_league_name}
            className="w-full bg-success hover:bg-success-hover text-white py-3 px-4 rounded-lg text-lg font-medium transition-colors shadow-sm focus:ring-2 focus:ring-success focus:ring-offset-2 outline-none disabled:bg-ui-light disabled:cursor-not-allowed"
        >
            {isLoading ? 'PUBLISHING...' : 'PUBLISH RESULT'}
        </button>
    );
};

export default LeaguePublish;