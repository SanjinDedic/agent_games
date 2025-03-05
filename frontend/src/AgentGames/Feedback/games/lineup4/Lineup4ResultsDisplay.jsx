import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';

const ResultsDisplay = ({ data, highlight = true, data_message = '', tablevisible }) => {
    const [results, setResults] = useState([]);
    const [tableColumns, setTableColumns] = useState([]);
    const [isTableVisible, setIsTableVisible] = useState(tablevisible);
    const userTeam = useSelector((state) => state.teams.currentTeam);

    useEffect(() => {
        if (data && data.total_points) {
            const teams = Object.keys(data.total_points);

            const resultData = teams.map(team => {
                // Extract game statistics from table data
                const wins = data.table?.wins?.[team] || 0;
                const draws = data.table?.draws?.[team] || 0;
                const gamesPlayed = data.table?.games_played?.[team] ||
                    Number(data.num_simulations) || 0;

                return {
                    team,
                    totalPoints: data.total_points[team],
                    gamesPlayed,
                    wins,
                    draws,
                    losses: gamesPlayed - wins - draws,
                    ...Object.fromEntries(
                        Object.entries(data.table || {})
                            .filter(([key]) => !['wins', 'draws', 'games_played'].includes(key))
                            .map(([key, values]) => [key, values[team]])
                    )
                };
            });

            // Sort by total points in descending order
            resultData.sort((a, b) => b.totalPoints - a.totalPoints);
            setResults(resultData);

            // Filter out special stat columns we handle separately
            const filteredColumns = Object.keys(data.table || {})
                .filter(key => !['wins', 'draws', 'games_played', 'total_draws'].includes(key));
            setTableColumns(filteredColumns);
        }
    }, [data]);

    useEffect(() => {
        setIsTableVisible(tablevisible);
    }, [data, tablevisible]);

    return (
        <div className="w-full">
            {data && (
                <h2 className="text-2xl font-bold text-ui-dark mb-6">{data_message}</h2>
            )}

            {!isTableVisible && (
                <button
                    onClick={() => setIsTableVisible(true)}
                    className="w-full py-2 px-4 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors duration-200"
                >
                    Show Results
                </button>
            )}

            {isTableVisible && (
                <div className="w-full overflow-x-auto bg-white rounded-lg shadow-lg border border-ui-light">
                    <table className="w-full border-collapse">
                        <thead>
                            <tr className="bg-league-blue text-white">
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Ranking</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Team</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Games Played</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Wins</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Draws</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Losses</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Total Points</th>
                                {tableColumns.map((column, index) => (
                                    <th key={index} className="p-4 text-left font-semibold border-b border-ui-light">
                                        {column}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {results.map((result, idx) => (
                                <tr
                                    key={result.team}
                                    className={`
                    ${idx % 2 === 0 ? 'bg-white' : 'bg-ui-lighter'}
                    ${highlight && result.team === userTeam ? 'bg-primary-light/20' : ''}
                    hover:bg-ui-lighter/70 transition-colors duration-150
                  `}
                                >
                                    <td className="p-4 border-b border-ui-light/30 font-medium">
                                        #{idx + 1}
                                    </td>
                                    <td className="p-4 border-b border-ui-light/30 font-medium">
                                        {result.team}
                                    </td>
                                    <td className="p-4 border-b border-ui-light/30 font-medium">
                                        {result.gamesPlayed?.toLocaleString() || 0}
                                    </td>
                                    <td className="p-4 border-b border-ui-light/30 font-medium text-success-hover">
                                        {result.wins?.toLocaleString() || 0}
                                    </td>
                                    <td className="p-4 border-b border-ui-light/30 font-medium text-amber-600">
                                        {result.draws?.toLocaleString() || 0}
                                    </td>
                                    <td className="p-4 border-b border-ui-light/30 font-medium text-danger">
                                        {result.losses?.toLocaleString() || 0}
                                    </td>
                                    <td className="p-4 border-b border-ui-light/30 font-medium text-primary-dark">
                                        {result.totalPoints?.toLocaleString() || 0}
                                    </td>
                                    {tableColumns.map((column, index) => (
                                        <td key={index} className="p-4 border-b border-ui-light/30">
                                            {result[column]}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

export default ResultsDisplay;