import React, { useState, useEffect } from "react";
import DiceDisplay from "./DiceDisplay";

const GreedyPigFeedback = ({ feedback }) => {
  const [currentRound, setCurrentRound] = useState(0);
  const [playerFilter, setPlayerFilter] = useState("all");
  const [allPlayers, setAllPlayers] = useState([]);

  // Extract player names when feedback changes
  useEffect(() => {
    if (feedback && feedback.rounds && feedback.rounds.length > 0) {
      const uniquePlayers = new Set();

      // Collect player names from all rounds and rolls
      feedback.rounds.forEach((round) => {
        round.rolls.forEach((roll) => {
          if (roll.player_states) {
            Object.keys(roll.player_states).forEach((player) => {
              uniquePlayers.add(player);
            });
          }
        });
      });

      setAllPlayers(Array.from(uniquePlayers).sort());
      setCurrentRound(0); // Reset to first round when feedback changes
    }
  }, [feedback]);

  if (!feedback || !feedback.rounds || !feedback.rounds.length) {
    return (
      <div className="p-4 text-ui-dark text-center">No game data available</div>
    );
  }

  // Get rounds based on filter
  const rounds = feedback.rounds || [];

  // Get current round data
  const roundData = rounds[currentRound] || null;

  // Get visible players for filtering
  const getVisiblePlayers = (roll) => {
    if (!roll.player_states) return {};

    if (playerFilter === "all") {
      return roll.player_states;
    }

    // Filter for specific player
    const filtered = {};
    if (roll.player_states[playerFilter]) {
      filtered[playerFilter] = roll.player_states[playerFilter];
    }
    return filtered;
  };

  // Render player action for a roll
  const renderPlayerAction = (player, state, roll) => {
    const action = state.action || "none";

    let actionDescription;
    let actionColor;

    if (roll.value === 1 && action === "lost_all") {
      actionDescription = "Lost all unbanked money!";
      actionColor = "text-danger font-bold";
    } else if (action === "bank") {
      actionDescription = `Banked $${state.unbanked_money}`;
      actionColor = "text-success font-bold";
    } else if (action === "continue") {
      actionDescription = "Continues rolling";
      actionColor = "text-primary italic";
    }

    return <div className={`${actionColor} ml-2`}>{actionDescription}</div>;
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg">
      {/* Filter controls */}
      <div className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-ui-dark font-medium mb-2">
            Player Filter:
          </label>
          <select
            value={playerFilter}
            onChange={(e) => setPlayerFilter(e.target.value)}
            className="w-full p-2 border border-ui-light rounded-lg bg-white text-ui-dark"
          >
            <option value="all">All Players</option>
            {allPlayers.map((player) => (
              <option key={player} value={player}>
                {player}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-ui-dark font-medium mb-2">Round:</label>
          <div className="flex items-center">
            <button
              onClick={() => setCurrentRound(Math.max(0, currentRound - 1))}
              disabled={currentRound === 0}
              className="p-2 bg-ui-lighter text-ui-dark rounded-l-lg disabled:opacity-50"
            >
              &larr;
            </button>
            <select
              value={currentRound}
              onChange={(e) => setCurrentRound(parseInt(e.target.value))}
              className="flex-grow p-2 border-y border-ui-light bg-white text-ui-dark text-center"
            >
              {rounds.map((round, index) => (
                <option key={index} value={index}>
                  Round {round.number || index + 1}
                </option>
              ))}
            </select>
            <button
              onClick={() =>
                setCurrentRound(Math.min(rounds.length - 1, currentRound + 1))
              }
              disabled={currentRound === rounds.length - 1}
              className="p-2 bg-ui-lighter text-ui-dark rounded-r-lg disabled:opacity-50"
            >
              &rarr;
            </button>
          </div>
        </div>
      </div>

      {/* Game visualization */}
      {roundData ? (
        <div className="bg-ui-lighter p-4 rounded-lg">
          <h3 className="text-xl font-bold text-ui-dark mb-4">
            Round {roundData.number || currentRound + 1}
          </h3>

          <div className="space-y-6">
            {roundData.rolls.map((roll, rollIndex) => {
              const visiblePlayers = getVisiblePlayers(roll);

              return (
                <div key={rollIndex} className="bg-white p-4 rounded-lg shadow">
                  <div className="flex items-center mb-4">
                    <span className="text-lg font-medium text-ui-dark mr-3">
                      Roll {roll.roll_number}:
                    </span>
                    <DiceDisplay value={roll.value} />

                    {roll.value === 1 && (
                      <span className="ml-4 text-danger font-bold">
                        Bust! All unbanked money lost
                      </span>
                    )}
                  </div>

                  {/* Players table */}
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="bg-ui-lighter">
                        <th className="p-2 text-left text-ui-dark">Player</th>
                        <th className="p-2 text-right text-ui-dark">
                          Unbanked
                        </th>
                        <th className="p-2 text-right text-ui-dark">Banked</th>
                        <th className="p-2 text-ui-dark">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(visiblePlayers).map(([player, state]) => (
                        <tr
                          key={player}
                          className="border-b border-ui-light/30"
                        >
                          <td className="p-2 font-medium">{player}</td>
                          <td className="p-2 text-right">
                            ${state.unbanked_money}
                          </td>
                          <td className="p-2 text-right">
                            ${state.banked_money}
                          </td>
                          <td className="p-2">
                            {renderPlayerAction(player, state, roll)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="text-center text-ui p-4">
          No data available for this round
        </div>
      )}

      {/* Final scores for the round if available */}
      {roundData && roundData.final_scores && (
        <div className="mt-6 bg-success/10 p-4 rounded-lg">
          <h3 className="text-lg font-bold text-ui-dark mb-2">
            Round End Scores
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {Object.entries(roundData.final_scores).map(([player, score]) => (
              <div key={player} className="bg-white p-3 rounded-lg shadow">
                <div className="font-medium">{player}</div>
                <div className="text-xl font-bold text-success">${score}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default GreedyPigFeedback;
