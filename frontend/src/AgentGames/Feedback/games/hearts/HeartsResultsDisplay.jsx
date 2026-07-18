import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import StrategyTooltip from '../../../Shared/Utilities/StrategyTooltip';
import { useTerms } from '../../../Shared/terminology';

// Hearts simulation rankings. total_points are tournament placement points
// (higher = better); the raw hearts score only appears as avg points per hand.
const HeartsResultsDisplay = ({ data, highlight = true, data_message = '', tablevisible }) => {
    const T = useTerms();
    const [results, setResults] = useState([]);
    const [isTableVisible, setIsTableVisible] = useState(tablevisible);
    const userTeam = useSelector((state) => state.teams.currentTeam);

    useEffect(() => {
        if (data && data.total_points) {
            const resultData = Object.keys(data.total_points).map((team) => ({
                team,
                totalPoints: data.total_points[team],
                gamesWon: data.table?.games_won?.[team] ?? 0,
                avgPointsPerHand: data.table?.avg_points_per_hand?.[team],
                moonsShot: data.table?.moons_shot?.[team] ?? 0,
                queensTaken: data.table?.queens_taken?.[team] ?? 0,
            }));
            resultData.sort((a, b) => b.totalPoints - a.totalPoints);
            setResults(resultData);
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
                                <th className="p-4 text-left font-semibold border-b border-ui-light">{T.Team}</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Games Won</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Avg Pts / Hand ↓</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Moons Shot 🌙</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Queens Taken</th>
                                <th className="p-4 text-left font-semibold border-b border-ui-light">Total Points</th>
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
                                        <StrategyTooltip name={result.team} strategy={data?.strategies?.[result.team]} />
                                    </td>
                                    <td className="p-4 border-b border-ui-light/30 font-medium text-success-hover">
                                        {result.gamesWon?.toLocaleString() || 0}
                                    </td>
                                    <td className="p-4 border-b border-ui-light/30 font-medium">
                                        {result.avgPointsPerHand ?? '—'}
                                    </td>
                                    <td className="p-4 border-b border-ui-light/30 font-medium text-amber-600">
                                        {result.moonsShot?.toLocaleString() || 0}
                                    </td>
                                    <td className="p-4 border-b border-ui-light/30 font-medium text-danger">
                                        {result.queensTaken?.toLocaleString() || 0}
                                    </td>
                                    <td className="p-4 border-b border-ui-light/30 font-medium text-primary-dark">
                                        {result.totalPoints?.toLocaleString() || 0}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    <div className="px-4 py-2 text-xs text-ui">
                        Total Points are tournament placement points across {data?.num_simulations?.toLocaleString()} games
                        (1st = 4, 2nd = 2, 3rd = 1, 4th = 0). Avg Pts / Hand is the raw Hearts score — lower is better.
                    </div>
                </div>
            )}
        </div>
    );
};

export default HeartsResultsDisplay;
