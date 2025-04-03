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
      const resultData = teams.map(team => ({
        team,
        totalPoints: data.total_points[team],
        gamesPlayed: data.num_simulations || 0,
        ...Object.fromEntries(
          Object.entries(data.table || {}).map(([key, values]) => [key, values[team]])
        )
      }));

      resultData.sort((a, b) => b.totalPoints - a.totalPoints);
      setResults(resultData);
      setTableColumns(Object.keys(data.table || {}));
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
                  <td className="p-4 border-b border-ui-light/30">
                    {result.gamesPlayed.toLocaleString()}
                  </td>
                  <td className="p-4 border-b border-ui-light/30 font-medium text-primary-dark">
                    {result.totalPoints.toLocaleString()}
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