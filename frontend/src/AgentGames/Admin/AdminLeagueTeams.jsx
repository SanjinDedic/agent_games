import './css/adminleague.css';
import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useSelector } from 'react-redux';

const AdminLeagueTeams = ({ selected_league_name }) => {
    const apiUrl = useSelector((state) => state.settings.agentApiUrl);
    const accessToken = useSelector((state) => state.auth.token);
    const [filteredTeams, setFilteredTeams] = useState([]);

    // useEffect(() => {
    //     if (!selected_league_name) return;

    //     fetch(apiUrl + '/get_all_teams')
    //       .then(response => response.json())
    //       .then(data => {
    //         if (data.status === "success" && Array.isArray(data.data.all_teams)) {
    
    //             const newFilteredTeams = data.data.all_teams.filter(value => value.league === selected_league_name);
    //             if (newFilteredTeams.length === 0) {
    //                 toast.error("No teams assigned to the League");
    //                 setFilteredTeams([]);
    //                 return;
    //             }
        
    //             setFilteredTeams(newFilteredTeams);
    //         } else if (data.status === "failed") {
    //           toast.error(data.message);
    //         }
    //       })
    //       .catch(error => {
    //         console.error('Error fetching options:', error);
    //       });
    //   }, [selected_league_name]);

    useEffect(() => {
        if (!selected_league_name) return;
        console.log(selected_league_name);
    fetch(`${apiUrl}/submitted_teams`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({ league_name: selected_league_name}),
    })
        .then(response => response.json())
        .then(data => {
            console.log(data);
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

