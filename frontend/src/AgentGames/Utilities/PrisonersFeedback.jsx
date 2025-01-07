import React, { useState, useMemo } from 'react';

const PrisonersFeedback = ({ feedback }) => {
  const [selectedPlayer, setSelectedPlayer] = useState('all');

  const players = useMemo(() => {
    return feedback.game_info.players;
  }, [feedback]);

  const getActionClass = (action1, action2) => {
    if (action1 === 'collude' && action2 === 'collude') return 'bg-success-light';
    if (action1 === 'defect' && action2 === 'defect') return 'bg-danger';
    return 'bg-danger-light'; // For mixed strategies (collude/defect or defect/collude)
  };

  const renderPairing = (pairing) => {
    const { player1, player2, rounds } = pairing;

    return (
      <div key={`${player1}-${player2}`} className="mb-6">
        <h3 className="text-lg font-semibold text-ui-dark mb-2">
          {player1} vs {player2}
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-ui-lighter">
                <th className="p-2 text-left font-medium text-sm text-ui-dark">Round</th>
                <th className="p-2 text-left font-medium text-sm text-ui-dark">{player1} Action</th>
                <th className="p-2 text-left font-medium text-sm text-ui-dark">{player2} Action</th>
                <th className="p-2 text-left font-medium text-sm text-ui-dark">{player1} Score</th>
                <th className="p-2 text-left font-medium text-sm text-ui-dark">{player2} Score</th>
              </tr>
            </thead>
            <tbody>
              {rounds.map((round) => (
                <tr
                  key={round.round_number}
                  className={`${getActionClass(round.actions[player1], round.actions[player2])} border border-ui-light`}
                >
                  <td className="p-2 text-sm">{round.round_number}</td>
                  <td className="p-2 text-sm">{round.actions[player1]}</td>
                  <td className="p-2 text-sm">{round.actions[player2]}</td>
                  <td className="p-2 text-sm">{round.scores[player1]}</td>
                  <td className="p-2 text-sm">{round.scores[player2]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
    <div className="bg-white p-4 rounded-lg shadow-md">
      <div className="mb-4">
        <label className="mr-2 text-ui-dark">View games for: </label>
        <select
          value={selectedPlayer}
          onChange={(e) => setSelectedPlayer(e.target.value)}
          className="p-1 border border-ui-light rounded bg-white text-ui-dark"
        >
          <option value="all">All Players</option>
          {players.map(player => (
            <option key={player} value={player}>{player}</option>
          ))}
        </select>
      </div>

      <div className="mb-6">
        <h2 className="text-xl font-semibold text-ui-dark mb-3">Final Scores</h2>
        <table className="min-w-[200px] border-collapse bg-white">
          <thead>
            <tr className="bg-ui-lighter">
              <th className="p-2 text-left font-medium text-sm text-ui-dark">Player</th>
              <th className="p-2 text-left font-medium text-sm text-ui-dark">Score</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(feedback.final_scores)
              .sort(([, a], [, b]) => b - a)
              .map(([player, score]) => (
                <tr key={player} className="border-b border-ui-light hover:bg-ui-lighter/50">
                  <td className="p-2 text-sm">{player}</td>
                  <td className="p-2 text-sm">{score}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <div className="space-y-6">
        {filteredPairings.map(renderPairing)}
      </div>
    </div>
  );
};

export default PrisonersFeedback;