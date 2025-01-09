import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useSelector } from 'react-redux';

const AdminLeagueTeams = ({ selected_league_name }) => {
    const teams = useSelector((state) => state.teams.list);
    const [filteredTeams, setFilteredTeams] = useState([]);

    useEffect(() => {
        if (!selected_league_name) return;

        const newFilteredTeams = teams.filter(value => value.league === selected_league_name);
        if (newFilteredTeams.length === 0) {
            toast.error("No teams assigned to the League");
            setFilteredTeams([]);
            return;
        }

        setFilteredTeams(newFilteredTeams);
    }, [selected_league_name, teams]);

    return (
        <div className="w-full">
            {filteredTeams.length > 0 && (
                <>
                    <h2 className="text-xl font-semibold text-ui-dark mb-6">Teams in League</h2>
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
                </>
            )}
        </div>
    );
};

export default AdminLeagueTeams;