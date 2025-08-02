import React from 'react';

const ArenaChampionsBattle = ({ battleData, currentTurn, battleComplete, turnIndex }) => {
    const { player1, player2, turns } = battleData;

    // Get HP values for current turn
    const getCurrentHP = () => {
        if (battleComplete && turns.length > 0) {
            return turns[turns.length - 1].hp;
        }
        if (currentTurn) {
            return currentTurn.hp;
        }
        // Initial HP values - we'll estimate based on damage patterns
        return { [player1]: 100, [player2]: 100 };
    };

    // Get previous HP to show damage taken
    const getPreviousHP = () => {
        if (turnIndex === 0) {
            // Estimate initial HP based on final HP and damage dealt
            const currentHP = getCurrentHP();
            const totalDamage1 = turns.reduce((sum, turn) => sum + (turn[`${player1}_damage`] || 0), 0);
            const totalDamage2 = turns.reduce((sum, turn) => sum + (turn[`${player2}_damage`] || 0), 0);
            
            return {
                [player1]: currentHP[player1] + totalDamage2,
                [player2]: currentHP[player2] + totalDamage1
            };
        }
        return turns[turnIndex - 1].hp;
    };

    const currentHP = getCurrentHP();
    const previousHP = getPreviousHP();

    // Calculate max HP for progress bars
    const getMaxHP = (player) => {
        const allHPValues = turns.map(turn => turn.hp[player]).filter(hp => hp !== undefined);
        const currentHPValue = currentHP[player];
        const previousHPValue = previousHP[player];
        
        return Math.max(currentHPValue, previousHPValue, ...allHPValues, 50); // minimum 50 for display
    };

    const maxHP1 = getMaxHP(player1);
    const maxHP2 = getMaxHP(player2);

    const getActionIcon = (action) => {
        switch (action) {
            case 'attack':
                return '⚔️';
            case 'defend':
                return '🛡️';
            case 'power_strike':
                return '💥';
            case 'analyze':
                return '🔍';
            case 'recovering':
                return '😵';
            default:
                return '❓';
        }
    };

    const getActionColor = (action) => {
        switch (action) {
            case 'attack':
                return 'text-danger';
            case 'defend':
                return 'text-primary';
            case 'power_strike':
                return 'text-purple-600';
            case 'analyze':
                return 'text-blue-600';
            case 'recovering':
                return 'text-amber-600';
            default:
                return 'text-ui';
        }
    };

    const getDamageInfo = (player) => {
        if (!currentTurn) return null;
        
        const damageDealt = currentTurn[`${player}_damage`];
        const healing = currentTurn[`${player}_healed`];
        const learnedHP = currentTurn[`${player}_learned_hp`];
        
        const info = [];
        if (damageDealt) info.push(`Dealt ${damageDealt} damage`);
        if (healing) info.push(`Healed ${healing} HP`);
        if (learnedHP !== undefined) info.push(`Learned opponent has ${learnedHP} HP`);
        
        return info.length > 0 ? info.join(', ') : null;
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
                                    <span>{currentHP[player1]}/{maxHP1}</span>
                                </div>
                                <div className="w-full bg-ui-lighter rounded-full h-4">
                                    <div
                                        className="bg-success h-4 rounded-full transition-all duration-500"
                                        style={{ width: `${Math.max(0, (currentHP[player1] / maxHP1) * 100)}%` }}
                                    />
                                </div>
                            </div>
                            
                            {currentTurn && (
                                <div className="space-y-2">
                                    <div className={`text-2xl ${getActionColor(currentTurn.actions[player1])}`}>
                                        {getActionIcon(currentTurn.actions[player1])}
                                    </div>
                                    <div className="text-sm font-medium capitalize">
                                        {currentTurn.actions[player1]}
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
                                    <span>{currentHP[player2]}/{maxHP2}</span>
                                </div>
                                <div className="w-full bg-ui-lighter rounded-full h-4">
                                    <div
                                        className="bg-success h-4 rounded-full transition-all duration-500"
                                        style={{ width: `${Math.max(0, (currentHP[player2] / maxHP2) * 100)}%` }}
                                    />
                                </div>
                            </div>
                            
                            {currentTurn && (
                                <div className="space-y-2">
                                    <div className={`text-2xl ${getActionColor(currentTurn.actions[player2])}`}>
                                        {getActionIcon(currentTurn.actions[player2])}
                                    </div>
                                    <div className="text-sm font-medium capitalize">
                                        {currentTurn.actions[player2]}
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
                            <h4 className="font-bold text-ui-dark mb-2">Turn {currentTurn.turn} Summary</h4>
                            <div className="text-sm text-ui space-y-1">
                                <div>
                                    <span className="font-medium text-primary">{player1}</span> used{' '}
                                    <span className="capitalize font-medium">{currentTurn.actions[player1]}</span>
                                    {currentTurn[`${player1}_damage`] && (
                                        <span className="text-danger"> (Dealt {currentTurn[`${player1}_damage`]} damage)</span>
                                    )}
                                </div>
                                <div>
                                    <span className="font-medium text-danger">{player2}</span> used{' '}
                                    <span className="capitalize font-medium">{currentTurn.actions[player2]}</span>
                                    {currentTurn[`${player2}_damage`] && (
                                        <span className="text-danger"> (Dealt {currentTurn[`${player2}_damage`]} damage)</span>
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
                            <h4 className="font-bold text-success text-lg mb-2">Battle Complete!</h4>
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
                <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-sm">
                    <div className="flex items-center gap-2">
                        <span className="text-danger">⚔️</span>
                        <span>Attack</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-primary">🛡️</span>
                        <span>Defend</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-purple-600">💥</span>
                        <span>Power Strike</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-blue-600">🔍</span>
                        <span>Analyze</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-amber-600">😵</span>
                        <span>Recovering</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ArenaChampionsBattle;