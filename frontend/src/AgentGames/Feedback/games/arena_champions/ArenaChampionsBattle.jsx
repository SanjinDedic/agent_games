import React from 'react';

const ArenaChampionsBattle = ({ battleData, currentTurn, battleComplete, turnIndex }) => {
  const { player1, player2, turns } = battleData;

  // Get HP values for current turn
  const getCurrentHP = () => {
    if (battleComplete && turns.length > 0) {
      return turns[turns.length - 1].health_after || {}; // ✅ Fixed: use health_after
    }
    if (currentTurn) {
      return currentTurn.health_after || {}; // ✅ Fixed: use health_after
    }
    // Initial HP values - we'll estimate based on damage patterns
    return { [player1]: 100, [player2]: 100 };
  };

  // Get previous HP to show damage taken
  const getPreviousHP = () => {
    if (turnIndex === 0) {
      // Estimate initial HP based on final HP and damage dealt
      const currentHP = getCurrentHP();
      const totalDamage1 = turns.reduce(
        (sum, turn) => sum + (turn.effects?.damage_dealt || 0),
        0
      );
      const totalDamage2 = turns.reduce(
        (sum, turn) => sum + (turn.effects?.damage_dealt || 0),
        0
      );

      return {
        [player1]: (currentHP[player1] || 0) + totalDamage2,
        [player2]: (currentHP[player2] || 0) + totalDamage1,
      };
    }
    return turns[turnIndex - 1]?.health_after || {}; // ✅ Fixed: use health_after with safe access
  };

  const currentHP = getCurrentHP();
  const previousHP = getPreviousHP();

  // Calculate max HP for progress bars
  const getMaxHP = (player) => {
    const allHPValues = turns
      .map((turn) => turn.health_after?.[player])
      .filter((hp) => hp !== undefined);
    const currentHPValue = currentHP[player] || 0;
    const previousHPValue = previousHP[player] || 0;

    return Math.max(currentHPValue, previousHPValue, ...allHPValues, 50); // minimum 50 for display
  };

  const maxHP1 = getMaxHP(player1);
  const maxHP2 = getMaxHP(player2);

  // ✅ Fixed: Get player action based on actual data structure
  const getPlayerAction = (player) => {
    if (!currentTurn) return null;

    // In Arena Champions, only the active player has an action each turn
    if (currentTurn.active_player === player) {
      return currentTurn.action;
    }

    // For the passive player, we don't have an action this turn
    return "waiting";
  };

  const getActionIcon = (action) => {
    switch (action) {
      case "attack":
        return "⚔️";
      case "big_attack":
        return "💥";
      case "defend":
        return "🛡️";
      case "dodge":
        return "🤸";
      case "run_away":
        return "🏃";
      case "waiting":
        return "⏳";
      default:
        return "❓";
    }
  };

  const getActionColor = (action) => {
    switch (action) {
      case "attack":
      case "big_attack":
        return "text-danger";
      case "defend":
        return "text-primary";
      case "dodge":
        return "text-purple-600";
      case "run_away":
        return "text-amber-600";
      case "waiting":
        return "text-ui";
      default:
        return "text-ui";
    }
  };

  // ✅ Fixed: Get damage info from effects
  const getDamageInfo = (player) => {
    if (!currentTurn || currentTurn.active_player !== player) return null;

    const effects = currentTurn.effects || {};
    const damageDealt = effects.damage_dealt;
    const healthCost = effects.health_cost;
    const ranAway = effects.ran_away;

    const info = [];
    if (damageDealt) info.push(`Dealt ${damageDealt} damage`);
    if (healthCost) info.push(`Lost ${healthCost} HP`);
    if (ranAway) info.push(`Ran away`);

    return info.length > 0 ? info.join(", ") : null;
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Battle Arena */}
      <div className="bg-gradient-to-b from-ui-lighter to-ui-light rounded-lg p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Player 1 */}
          <div className="text-center">
            <h3 className="text-lg font-bold text-primary mb-2">{player1}</h3>
            <div className="bg-white rounded-lg p-4 shadow-md">
              <div className="mb-3">
                <div className="flex justify-between text-sm text-ui mb-1">
                  <span>HP</span>
                  <span>
                    {currentHP[player1] || 0}/{maxHP1}
                  </span>
                </div>
                <div className="w-full bg-ui-lighter rounded-full h-4">
                  <div
                    className="bg-success h-4 rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.max(
                        0,
                        ((currentHP[player1] || 0) / maxHP1) * 100
                      )}%`,
                    }}
                  />
                </div>
              </div>

              {currentTurn && (
                <div className="space-y-2">
                  <div
                    className={`text-2xl ${getActionColor(
                      getPlayerAction(player1)
                    )}`}
                  >
                    {getActionIcon(getPlayerAction(player1))}
                  </div>
                  <div className="text-sm font-medium capitalize">
                    {getPlayerAction(player1)}
                  </div>
                  {getDamageInfo(player1) && (
                    <div className="text-xs text-ui bg-ui-lighter p-2 rounded">
                      {getDamageInfo(player1)}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Player 2 */}
          <div className="text-center">
            <h3 className="text-lg font-bold text-danger mb-2">{player2}</h3>
            <div className="bg-white rounded-lg p-4 shadow-md">
              <div className="mb-3">
                <div className="flex justify-between text-sm text-ui mb-1">
                  <span>HP</span>
                  <span>
                    {currentHP[player2] || 0}/{maxHP2}
                  </span>
                </div>
                <div className="w-full bg-ui-lighter rounded-full h-4">
                  <div
                    className="bg-success h-4 rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.max(
                        0,
                        ((currentHP[player2] || 0) / maxHP2) * 100
                      )}%`,
                    }}
                  />
                </div>
              </div>

              {currentTurn && (
                <div className="space-y-2">
                  <div
                    className={`text-2xl ${getActionColor(
                      getPlayerAction(player2)
                    )}`}
                  >
                    {getActionIcon(getPlayerAction(player2))}
                  </div>
                  <div className="text-sm font-medium capitalize">
                    {getPlayerAction(player2)}
                  </div>
                  {getDamageInfo(player2) && (
                    <div className="text-xs text-ui bg-ui-lighter p-2 rounded">
                      {getDamageInfo(player2)}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Turn Summary */}
        {currentTurn && (
          <div className="mt-6 text-center">
            <div className="bg-white rounded-lg p-4 shadow-md">
              <h4 className="font-bold text-ui-dark mb-2">
                Turn {currentTurn.turn} Summary
              </h4>
              <div className="text-sm text-ui space-y-1">
                <div>
                  <span className="font-medium text-primary">
                    {currentTurn.active_player}
                  </span>{" "}
                  used{" "}
                  <span className="capitalize font-medium">
                    {currentTurn.action}
                  </span>
                  {currentTurn.effects?.damage_dealt && (
                    <span className="text-danger">
                      {" "}
                      (Dealt {currentTurn.effects.damage_dealt} damage)
                    </span>
                  )}
                  {currentTurn.effects?.health_cost && (
                    <span className="text-amber-600">
                      {" "}
                      (Lost {currentTurn.effects.health_cost} HP)
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Battle Complete */}
        {battleComplete && (
          <div className="mt-6 text-center">
            <div className="bg-success/20 border-2 border-success rounded-lg p-4">
              <h4 className="font-bold text-success text-lg mb-2">
                Battle Complete!
              </h4>
              <div className="text-success font-medium">
                🏆 {battleData.winner} Wins!
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Action Legend */}
      <div className="bg-white rounded-lg p-4 shadow-md">
        <h4 className="font-bold text-ui-dark mb-3">Action Legend</h4>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-2 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-danger">⚔️</span>
            <span>Attack</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-danger">💥</span>
            <span>Big Attack</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-primary">🛡️</span>
            <span>Defend</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-purple-600">🤸</span>
            <span>Dodge</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-amber-600">🏃</span>
            <span>Run Away</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-ui">⏳</span>
            <span>Waiting</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ArenaChampionsBattle;