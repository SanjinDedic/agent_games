import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';

const ArenaChampionsResultsDisplay = ({ data, highlight = true, data_message = '', tablevisible }) => {
    const [results, setResults] = useState([]);
    const [tableColumns, setTableColumns] = useState([]);
    const [isTableVisible, setIsTableVisible] = useState(tablevisible);
    const userTeam = useSelector((state) => state.teams.currentTeam);

    useEffect(() => {
        if (data && data.total_points) {
            const teams = Object.keys(data.total_points);

            const resultData = teams.map(team => {
                // Extract battle statistics from table data
                const wins = data.table?.wins?.[team] || 0;
                const losses = data.table?.losses?.[team] || 0;
                const battlesPlayed = data.table?.battles_played?.[team] ||
                    Number(data.num_simulations) || 0;

                return {
                    team,
                    totalPoints: data.total_points[team],
                    battlesPlayed,
                    wins,
                    losses,
                    winRate: battlesPlayed > 0 ? ((wins / battlesPlayed) * 100).toFixed(1) : '0.0',
                    ...Object.fromEntries(
                        Object.entries(data.table || {})
                            .filter(([key]) => !['wins', 'losses', 'battles_played'].includes(key))
                            .map(([key, values]) => [key, values[team]])
                    )
                };
            });

            // Sort by total points in descending order
            resultData.sort((a, b) => b.totalPoints - a.totalPoints);
            setResults(resultData);

            // Filter out special stat columns we handle separately
            const filteredColumns = Object.keys(data.table || {})
                .filter(key => !['wins', 'losses', 'battles_played'].includes(key));
            setTableColumns(filteredColumns);
        }
    }, [data]);

    useEffect(() => {
        setIsTableVisible(tablevisible);
    }, [data, tablevisible]);

    const getRankingBadge = (index) => {
        if (index === 0) return '🥇';
        if (index === 1) return '🥈';
        if (index === 2) return '🥉';
        return `#${index + 1}`;
    };

    const getWinRateColor = (winRate) => {
        const rate = parseFloat(winRate);
        if (rate >= 70) return 'text-success';
        if (rate >= 50) return 'text-amber-600';
        return 'text-danger';
    };

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
                    Show Arena Champions Results
                </button>
            )}

            {isTableVisible && (
                <div className="w-full overflow-x-auto bg-white rounded-lg shadow-lg border border-ui-light">
                    <table className="w-full border-collapse">
                        <thead>
                            <tr className="bg-gradient-to-r from-purple-600 to-red-600 text-white">
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Ranking</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Champion</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Battles</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Wins</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Losses</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Win Rate</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Total Points</th>
                                {tableColumns.map((column, index) => (
                                    <th key={index} className="p-4 text-left font-semibold border-b border-ui-light">
                                        {column.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
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
                                        ${idx === 0 ? 'bg-gradient-to-r from-yellow-50 to-amber-50' : ''}
                                        hover:bg-ui-lighter/70 transition-colors duration-150
                                    `}
                                >
                                    <td className="p-4 border-b border-ui-light/30 font-medium">
                                        <div className="flex items-center gap-2">
                                            <span className="text-lg">{getRankingBadge(idx)}</span>
                                        </div>
                                    </td>
                                    <td className="p-4 border-b border-ui-light/30 font-medium">
                                        <div className="flex items-center gap-2">
                                            <span className="text-lg">⚔️</span>
                                            <span className={idx === 0 ? 'font-bold text-amber-600' : ''}>{result.team}</span>
                                        </div>
                                    </td>
                                    <td className="p-4 border-b border-ui-light/30 font-medium">
                                        {result.battlesPlayed?.toLocaleString() || 0}
                                    </td>
                                    <td className="p-4 border-b border-ui-light/30 font-medium text-success">
                                        {result.wins?.toLocaleString() || 0}
                                    </td>
                                    <td className="p-4 border-b border-ui-light/30 font-medium text-danger">
                                        {result.losses?.toLocaleString() || 0}
                                    </td>
                                    <td className={`p-4 border-b border-ui-light/30 font-medium ${getWinRateColor(result.winRate)}`}>
                                        {result.winRate}%
                                    </td>
                                    <td className="p-4 border-b border-ui-light/30 font-medium text-primary-dark">
                                        <div className="flex items-center gap-1">
                                            <span className="text-lg">🏆</span>
                                            <span className="font-bold">{result.totalPoints?.toLocaleString() || 0}</span>
                                        </div>
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

            {/* Arena Champions Legend */}
            {isTableVisible && (
                <div className="mt-6 bg-white rounded-lg p-4 shadow-md border border-ui-light">
                    <h3 className="font-bold text-ui-dark mb-3">Arena Champions Scoring</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                        <div className="space-y-2">
                            <div className="flex items-center gap-2">
                                <span className="text-success">🏆</span>
                                <span>Victory: Points awarded for winning battles</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-amber-600">⚔️</span>
                                <span>Combat performance matters</span>
                            </div>
                        </div>
                        <div className="space-y-2">
                            <div className="flex items-center gap-2">
                                <span className="text-primary">📊</span>
                                <span>Win Rate: Percentage of battles won</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-ui">🎯</span>
                                <span>Strategy and adaptation are key</span>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ArenaChampionsResultsDisplay;