import './css/adminleague.css';
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


    }, [selected_league_name]);


    const rows = [];
    for (let i = 0; i < filteredTeams.length; i += 4) {
        const row = filteredTeams.slice(i, i + 4);
        rows.push(row);
    }

    return (
        <>
            {filteredTeams.length > 0 && (
                <table border="1">
                    <thead>
                    </thead>
                    <tbody>
                        {rows.map((row, rowIndex) => (
                            <tr key={rowIndex}>
                                {row.map((team, colIndex) => (
                                    <td key={colIndex}>
                                        <div className="table-cell">
                                            {team.name}

                                        </div>
                                    </td>
                                ))}
                                {row.length < 4 && Array.from({ length: 4 - row.length }).map((_, colIndex) => (
                                    <td key={colIndex + row.length}></td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>)}
        </>
    );
}

export default AdminLeagueTeams;

