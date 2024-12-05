import React, { useState, useMemo } from 'react';
import './css/PrisonersFeedback.css';

const PrisonersFeedback = ({ feedback }) => {
  const [selectedPlayer, setSelectedPlayer] = useState('all');

  const players = useMemo(() => {
    return feedback.game_info.players;
  }, [feedback]);

  const getActionClass = (action1, action2) => {
    if (action1 === 'collude' && action2 === 'collude') return 'collude_collude';
    if (action1 === 'defect' && action2 === 'defect') return 'defect_defect';
    return 'mixed_strategy';
  };

  const renderPairing = (pairing) => {
    const { player1, player2, rounds } = pairing;
    
    return (
      <div key={`${player1}-${player2}`}>
        <h3>{player1} vs {player2}</h3>
        <table>
          <thead>
            <tr>
              <th>Round</th>
              <th>{player1} Action</th>
              <th>{player2} Action</th>
              <th>{player1} Score</th>
              <th>{player2} Score</th>
            </tr>
          </thead>
          <tbody>
            {rounds.map((round) => (
              <tr 
                key={round.round_number}
                className={getActionClass(round.actions[player1], round.actions[player2])}
              >
                <td>{round.round_number}</td>
                <td>{round.actions[player1]}</td>
                <td>{round.actions[player2]}</td>
                <td>{round.scores[player1]}</td>
                <td>{round.scores[player2]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const filteredPairings = useMemo(() => {
    if (selectedPlayer === 'all') return feedback.pairings;
    return feedback.pairings.filter(
      pairing => pairing.player1 === selectedPlayer || pairing.player2 === selectedPlayer
    );
  }, [feedback.pairings, selectedPlayer]);

  return (
    <div className="prisoners_dilemma">
      <div>
        <label>View games for: </label>
        <select 
          value={selectedPlayer}
          onChange={(e) => setSelectedPlayer(e.target.value)}
        >
          <option value="all">All Players</option>
          {players.map(player => (
            <option key={player} value={player}>{player}</option>
          ))}
        </select>
      </div>

      <div>
        <h2>Final Scores</h2>
        <table className="scores_table">
          <thead>
            <tr>
              <th>Player</th>
              <th>Score</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(feedback.final_scores)
              .sort(([, a], [, b]) => b - a)
              .map(([player, score]) => (
                <tr key={player}>
                  <td>{player}</td>
                  <td>{score}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <div>
        {filteredPairings.map(renderPairing)}
      </div>
    </div>
  );
};

export default PrisonersFeedback;