import React from 'react';

const GreedyPigRoundView = ({ roll, allPlayers, selectedPlayer }) => {
    const playersInRoll = roll.players || [];
    const displayPlayers = selectedPlayer === 'all'
        ? allPlayers
        : [selectedPlayer];

    // Build a lookup from the roll data
    const playerDataMap = {};
    playersInRoll.forEach(p => {
        playerDataMap[p.name] = p;
    });

    return (
        <div className="max-w-[700px] mx-auto">
            <div className="overflow-x-auto bg-ui-lighter rounded-lg">
                <table className="w-full border-collapse">
                    <thead>
                        <tr className="bg-league-blue text-white">
                            <th className="p-3 text-left font-semibold border-b border-ui-light">
                                {roll.busted ? (
                                    <span>Dice: <span className="text-danger-light font-bold">{roll.dice_value}</span></span>
                                ) : (
                                    <span>Dice: <span className="font-bold">{roll.dice_value}</span></span>
                                )}
                            </th>
                            {displayPlayers.map(name => (
                                <th key={name} className="p-3 text-center font-semibold border-b border-ui-light">
                                    {name}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        <tr className="bg-white">
                            <td className="p-3 font-medium text-ui-dark border-b border-ui-light/30">
                                Unbanked
                            </td>
                            {displayPlayers.map(name => {
                                const pData = playerDataMap[name];
                                if (!pData) return <td key={name} className="p-3 text-center border-b border-ui-light/30 text-ui">-</td>;
                                const lost = roll.busted && pData.lost_money;
                                return (
                                    <td key={name} className={`p-3 text-center border-b border-ui-light/30 font-medium ${lost ? 'text-danger' : 'text-ui-dark'}`}>
                                        {roll.busted ? (
                                            lost ? (
                                                <span>${pData.unbanked_before} &rarr; $0</span>
                                            ) : (
                                                <span>$0</span>
                                            )
                                        ) : (
                                            <span>${pData.unbanked}</span>
                                        )}
                                    </td>
                                );
                            })}
                        </tr>
                        <tr className={displayPlayers.length % 2 === 0 ? 'bg-ui-lighter' : 'bg-white'}>
                            <td className="p-3 font-medium text-ui-dark border-b border-ui-light/30">
                                Banked
                            </td>
                            {displayPlayers.map(name => {
                                const pData = playerDataMap[name];
                                if (!pData) return <td key={name} className="p-3 text-center border-b border-ui-light/30 text-ui">-</td>;
                                return (
                                    <td key={name} className="p-3 text-center border-b border-ui-light/30 font-medium text-success-hover">
                                        ${pData.banked}
                                    </td>
                                );
                            })}
                        </tr>
                        {!roll.busted && (
                            <tr className="bg-white">
                                <td className="p-3 font-medium text-ui-dark">
                                    Action
                                </td>
                                {displayPlayers.map(name => {
                                    const pData = playerDataMap[name];
                                    if (!pData) return <td key={name} className="p-3 text-center text-ui">-</td>;
                                    const action = pData.action;
                                    return (
                                        <td key={name} className="p-3 text-center">
                                            {action === 'bank' ? (
                                                <span className="inline-block px-3 py-1 rounded-full bg-success-light text-success-hover font-medium text-sm">
                                                    Bank
                                                </span>
                                            ) : action === 'continue' ? (
                                                <span className="inline-block px-3 py-1 rounded-full bg-primary-light/20 text-primary font-medium text-sm">
                                                    Continue
                                                </span>
                                            ) : (
                                                <span className="text-ui">-</span>
                                            )}
                                        </td>
                                    );
                                })}
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default GreedyPigRoundView;
