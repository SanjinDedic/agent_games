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
        <h2 className="text-xl font-semibold text-ui-dark mb-4">{data_message}</h2>
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
        <div className="w-full overflow-x-auto">
          <table className="w-full min-w-[600px] border-collapse bg-white">
            <thead>
              <tr className="bg-ui-lighter">
                <th className="p-3 text-left font-semibold text-ui-dark">Team</th>
                <th className="p-3 text-left font-semibold text-ui-dark">Total Points</th>
                {tableColumns.map((column, index) => (
                  <th key={index} className="p-3 text-left font-semibold text-ui-dark">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {results.map((result) => (
                <tr
                  key={result.team}
                  className={`
                    border-b border-ui-light/20
                    ${highlight && result.team === userTeam
                      ? 'bg-primary-light/20 hover:bg-primary-light/30'
                      : 'hover:bg-ui-lighter/50'}
                  `}
                >
                  <td className="p-3">{result.team}</td>
                  <td className="p-3">{result.totalPoints}</td>
                  {tableColumns.map((column, index) => (
                    <td key={index} className="p-3">{result[column]}</td>
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