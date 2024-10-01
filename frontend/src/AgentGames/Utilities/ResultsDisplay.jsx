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

      // Sort teams by points descending
      resultData.sort((a, b) => b.totalPoints - a.totalPoints);

      setResults(resultData);
      setTableColumns(Object.keys(data.table || {}));
    }
  }, [data]);

  useEffect(() => {
    setIsTableVisible(tablevisible);
  }, [data, tablevisible]);

  return (
    <div className="results-container">
      {data && <h2>{data_message}</h2>}

      {!isTableVisible && (
            <button onClick={() => setIsTableVisible(!isTableVisible)} className="publish-button" style={{ cursor: 'pointer' }}>
              {isTableVisible ? 'Hide Results' : 'Show Results'}
            </button>
          )}

      {isTableVisible && (
      <table>
        <thead>
          <tr>
            <th>Team</th>
            <th>Total Points</th>
            {tableColumns.map((column, index) => (
              <th key={index}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {results.map((result) => (
            <tr key={result.team} className={highlight && result.team === userTeam ? 'highlighted' : ''}>
              <td>{result.team}</td>
              <td>{result.totalPoints}</td>
              {tableColumns.map((column, index) => (
                <td key={index}>{result[column]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      )}
    </div>
  );
};

export default ResultsDisplay;