import React, { useState, useEffect } from 'react';
import ArenaChampionsBattle from './ArenaChampionsBattle';
import ArenaChampionsPlayerFeedback from './ArenaChampionsPlayerFeedback';

const ArenaChampionsFeedback = ({ feedback }) => {
  const [selectedPlayer, setSelectedPlayer] = useState("all");
  const [selectedBattle, setSelectedBattle] = useState(0);
  const [currentTurnIndex, setCurrentTurnIndex] = useState(0);
  const [battleComplete, setBattleComplete] = useState(false);
  const [filteredBattles, setFilteredBattles] = useState([]);
  const [players, setPlayers] = useState([]);

  useEffect(() => {
    if (feedback?.battles) {
      const uniquePlayers = new Set();
      feedback.battles.forEach((battle) => {
        uniquePlayers.add(battle.player1);
        uniquePlayers.add(battle.player2);
      });
      setPlayers(Array.from(uniquePlayers).sort());
      setFilteredBattles(feedback.battles);
    }
  }, [feedback]);

  useEffect(() => {
    if (feedback?.battles) {
      const battles =
        selectedPlayer === "all"
          ? feedback.battles
          : feedback.battles.filter(
              (battle) =>
                battle.player1 === selectedPlayer ||
                battle.player2 === selectedPlayer
            );

      setFilteredBattles(battles);
      setSelectedBattle(0);
      setCurrentTurnIndex(0);
      setBattleComplete(false);
    }
  }, [selectedPlayer, feedback]);

  if (!feedback?.battles || feedback.battles.length === 0) {
    return <div className="text-ui-dark">No battle data available</div>;
  }

  if (filteredBattles.length === 0) {
    return (
      <div className="text-ui-dark">
        No battles found for the selected filters
      </div>
    );
  }

  const currentBattleData =
    filteredBattles[selectedBattle] || filteredBattles[0];
  if (!currentBattleData) {
    return <div className="text-ui-dark">Battle data not available</div>;
  }

  const turns = currentBattleData.turns || [];
  const winner = currentBattleData.winner;
  const player1 = currentBattleData.player1;
  const player2 = currentBattleData.player2;

  // ✅ Fixed: Handle missing preview data gracefully
  const matchInfo = currentBattleData.match_info || {};
  const matchType = matchInfo.type || "unknown";
  const firstPlayer = matchInfo.first_player || player1;

  const handlePlayerChange = (e) => {
    setSelectedPlayer(e.target.value);
  };

  const handleBattleChange = (e) => {
    const battleIndex = parseInt(e.target.value);
    setSelectedBattle(battleIndex);
    setCurrentTurnIndex(0);
    setBattleComplete(false);
  };

  const handleNext = () => {
    if (currentTurnIndex < turns.length - 1) {
      setCurrentTurnIndex(currentTurnIndex + 1);
    } else if (currentTurnIndex === turns.length - 1) {
      setBattleComplete(true);
    }
  };

  const handlePrevious = () => {
    if (currentTurnIndex > 0) {
      setCurrentTurnIndex(currentTurnIndex - 1);
      setBattleComplete(false);
    }
  };

  const getCurrentTurn = () => {
    if (battleComplete || !turns[currentTurnIndex]) return null;
    return turns[currentTurnIndex];
  };

  const getPlayerColor = (player) => {
    return player === player1 ? "text-primary" : "text-danger";
  };

  // ✅ Fixed: Create battle description based on actual data
  const getBattleDescription = (battle, index) => {
    const matchInfo = battle.match_info || {};
    const matchType = matchInfo.type || "battle";
    const firstPlayer = matchInfo.first_player || battle.player1;

    return `${battle.player1} vs ${battle.player2} (${
      matchType === "home" ? `${firstPlayer} goes first` : "standard match"
    })`;
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg">
      <div className="mb-6 space-y-4">
        <div>
          <label className="block text-ui-dark font-medium mb-2">
            Select Player
          </label>
          <select
            value={selectedPlayer}
            onChange={handlePlayerChange}
            className="w-full p-3 border border-ui-light rounded-lg bg-white text-ui-dark"
          >
            <option value="all">All Players</option>
            {players.map((player) => (
              <option key={player} value={player}>
                {player}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-ui-dark font-medium mb-2">
            Select Battle
          </label>
          <select
            value={selectedBattle}
            onChange={handleBattleChange}
            className="w-full p-3 border border-ui-light rounded-lg bg-white text-ui-dark"
          >
            {filteredBattles.map((battle, index) => (
              <option key={index} value={index}>
                {getBattleDescription(battle, index)}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mb-6 text-center">
        <h2 className="text-xl font-bold mb-2 flex items-center justify-center gap-2">
          <span className={getPlayerColor(player1)}>{player1}</span>
          <span className="text-ui-dark">vs</span>
          <span className={getPlayerColor(player2)}>{player2}</span>
        </h2>
        <div className="flex items-center justify-center gap-4 text-sm text-ui mb-2">
          <span
            className={`px-2 py-1 rounded ${
              matchType === "home"
                ? "bg-success/20 text-success"
                : "bg-ui-lighter text-ui"
            }`}
          >
            {matchType === "home"
              ? `${firstPlayer} goes first`
              : "Standard Battle"}
          </span>
        </div>
        <div className="text-lg">
          {battleComplete ? (
            <div className="text-success font-semibold">Winner: {winner}</div>
          ) : (
            getCurrentTurn() && (
              <div className="text-ui">
                Turn {currentTurnIndex + 1} of {turns.length}
              </div>
            )
          )}
        </div>
      </div>

      <ArenaChampionsBattle
        battleData={currentBattleData}
        currentTurn={getCurrentTurn()}
        battleComplete={battleComplete}
        turnIndex={currentTurnIndex}
      />

      <div className="flex justify-center items-center gap-6 mt-6">
        <button
          onClick={handlePrevious}
          disabled={currentTurnIndex === 0}
          className="px-6 py-3 text-lg rounded-lg bg-ui-lighter hover:bg-ui-light disabled:opacity-50 disabled:cursor-not-allowed"
        >
          ←
        </button>
        <span className="text-lg text-ui-dark">
          {battleComplete
            ? "Battle Complete"
            : `Turn ${currentTurnIndex + 1} of ${turns.length}`}
        </span>
        <button
          onClick={handleNext}
          disabled={battleComplete}
          className="px-6 py-3 text-lg rounded-lg bg-ui-lighter hover:bg-ui-light disabled:opacity-50 disabled:cursor-not-allowed"
        >
          →
        </button>
      </div>

      {/* Display turn feedback */}
      {getCurrentTurn() && (
        <ArenaChampionsPlayerFeedback
          currentTurn={getCurrentTurn()}
          battleData={currentBattleData}
          feedback={feedback}
        />
      )}
    </div>
  );
};

export default ArenaChampionsFeedback;