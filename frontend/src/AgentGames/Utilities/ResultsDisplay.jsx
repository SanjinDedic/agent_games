import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { } from '../../slices/rankingsSlice'

const ResultsDisplay = ({ data, highlight = true, data_message = '' }) => {
  const [results, setResults] = useState([]);
  const userTeam = useSelector((state) => state.teams.currentTeam);
  
    useEffect(() => {
    if (data.length > 0 && data[0].hasOwnProperty('name')) {

      const resultData = data.map(item => ({
        team: item.name,
        totalPoints: 0,
        totalWins: 0
      }));


      setResults(resultData);
    }
    else if (data) {
      const teams = Object.keys(data.total_points || {});
      const resultData = teams.map(team => ({
        team,
        totalPoints: data.total_points[team],
        totalWins: data.total_wins[team]
      }));

      // Sort teams by points descending
      resultData.sort((a, b) => b.totalPoints - a.totalPoints);

      setResults(resultData);
    }
  }, [data]);

  return (
    <div className="results-container">
      {data && <h2>{data_message}</h2>}

      <table>
        <thead>
          <tr>
            <th>Team</th>
            <th>Total Points</th>
            <th>Total Wins</th>
          </tr>
        </thead>
        <tbody>
          {results.map(({ team, totalPoints, totalWins }) => (
            <tr key={team} className={highlight && team === userTeam ? 'highlighted' : ''}>
              <td>{team}</td>
              <td>{totalPoints}</td>
              <td>{totalWins}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ResultsDisplay;
