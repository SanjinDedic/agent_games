import React from 'react';
import { formatNumber } from "../../../../utils/numberFormat";

const ArenaChampionsBattle = ({
  battleData,
  currentTurn,
  battleComplete,
  turnIndex,
}) => {
  const { player1, player2, turns } = battleData;

  // Get HP values directly from backend data - no complex calculations needed!
  const getCurrentHP = () => {
    if (battleComplete && turns.length > 0) {
      // Show final HP after last turn
      return turns[turns.length - 1].health_after || {};
    }
    if (currentTurn && currentTurn.health_after) {
      // Show HP after current turn
      return currentTurn.health_after;
    }
    if (currentTurn && currentTurn.health_before) {
      // Fallback: show HP before current turn if after isn't available
      return currentTurn.health_before;
    }
    // Initial state: use first turn's health_before if available
    if (turns.length > 0 && turns[0].health_before) {
      return turns[0].health_before;
    }
    return { [player1]: 0, [player2]: 0 };
  };

  const currentHP = getCurrentHP();

  // Calculate max HP for progress bars - find the highest HP value any player has had
  const getMaxHP = (player) => {
    let maxHP = 50; // minimum fallback

    turns.forEach((turn) => {
      if (turn.health_before && turn.health_before[player] !== undefined) {
        maxHP = Math.max(maxHP, turn.health_before[player]);
      }
      if (turn.health_after && turn.health_after[player] !== undefined) {
        maxHP = Math.max(maxHP, turn.health_after[player]);
      }
    });

    return maxHP;
  };

  const maxHP1 = getMaxHP(player1);
  const maxHP2 = getMaxHP(player2);

  // ✅ Fixed: Get player action based on new data structure
  const getPlayerAction = (player) => {
    if (!currentTurn) return null;

    // In the new structure, we have attacker/defender with their respective actions
    if (currentTurn.attacker === player) {
      return currentTurn.attack_action;
    } else if (currentTurn.defender === player) {
      return currentTurn.defend_action;
    }

    // If player is not involved in this turn
    return "waiting";
  };

  const getActionIcon = (action) => {
    switch (action) {
      case "attack":
        return "⚔️";
      case "big_attack":
        return "💥";
      case "multiattack":
        return "🔥";
      case "precise_attack":
        return "🎯";
      case "defend":
        return "🛡️";
      case "dodge":
        return "🤸";
      case "brace":
        return "🔒";
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
      case "multiattack":
      case "precise_attack":
        return "text-danger";
      case "defend":
        return "text-primary";
      case "dodge":
        return "text-purple-600";
      case "brace":
        return "text-amber-600";
      case "waiting":
        return "text-ui";
      default:
        return "text-ui";
    }
  };

  // ✅ Fixed: Get damage info from new effects structure
  const getDamageInfo = (player) => {
    if (!currentTurn) return null;

    const effects = currentTurn.effects || {};
    const info = [];

    // If this player is the attacker
    if (currentTurn.attacker === player) {
      const damageDealt = effects.damage_dealt;
      const attackerHealthCost = effects.attacker_health_cost;

      if (damageDealt) info.push(`Dealt ${formatNumber(damageDealt)} damage`);
      if (attackerHealthCost)
        info.push(`Lost ${formatNumber(attackerHealthCost)} HP`);
    }

    // If this player is the defender
    if (currentTurn.defender === player) {
      const defenseResult = effects.defense_result;
      if (defenseResult) {
        // Format any numbers in the defense result text
        const formattedResult = defenseResult.replace(
          /(\d+\.?\d*)/g,
          (match) => {
            const num = parseFloat(match);
            return !isNaN(num) ? formatNumber(num) : match;
          }
        );
        info.push(formattedResult);
      }
    }

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
                    {formatNumber(currentHP[player1] || 0)}/
                    {formatNumber(maxHP1)}
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
                    {formatNumber(currentHP[player2] || 0)}/
                    {formatNumber(maxHP2)}
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
                Turn {currentTurn.turn || turnIndex + 1} Summary
              </h4>
              <div className="text-sm text-ui space-y-1">
                <div>
                  <span className="font-medium text-primary">
                    {currentTurn.attacker}
                  </span>{" "}
                  used{" "}
                  <span className="capitalize font-medium text-danger">
                    {currentTurn.attack_action}
                  </span>
                  {currentTurn.effects?.damage_dealt && (
                    <span className="text-danger">
                      {" "}
                      (Dealt {formatNumber(
                        currentTurn.effects.damage_dealt
                      )}{" "}
                      damage)
                    </span>
                  )}
                  {currentTurn.effects?.attacker_health_cost && (
                    <span className="text-amber-600">
                      {" "}
                      (Lost{" "}
                      {formatNumber(
                        currentTurn.effects.attacker_health_cost
                      )}{" "}
                      HP)
                    </span>
                  )}
                </div>
                <div>
                  <span className="font-medium text-purple-600">
                    {currentTurn.defender}
                  </span>{" "}
                  used{" "}
                  <span className="capitalize font-medium text-purple-600">
                    {currentTurn.defend_action}
                  </span>
                  {currentTurn.effects?.defense_result && (
                    <span className="text-ui">
                      {" "}
                      (
                      {currentTurn.effects.defense_result.replace(
                        /(\d+\.?\d*)/g,
                        (match) => {
                          const num = parseFloat(match);
                          return !isNaN(num) ? formatNumber(num) : match;
                        }
                      )}
                      )
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
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-danger">⚔️</span>
            <span>Attack</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-danger">💥</span>
            <span>Big Attack</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-danger">🔥</span>
            <span>Multiattack</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-danger">🎯</span>
            <span>Precise Attack</span>
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
            <span className="text-amber-600">🔒</span>
            <span>Brace</span>
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