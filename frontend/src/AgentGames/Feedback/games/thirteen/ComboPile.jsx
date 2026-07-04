import React from 'react';
import CardRow from '../../../Shared/Cards/CardRow';

// The central pile: the combo currently on the table that must be beaten, or an
// empty table when a fresh lead is about to happen. Replaces TrickDisplay for a
// shedding game, where each entry is a variable-length combo rather than one
// card per seat.
const ComboPile = ({ combo = [], owner, userPlayer }) => {
    const empty = !combo || combo.length === 0;

    return (
        <div className="flex flex-col items-center gap-2 py-4 bg-ui-lighter rounded-lg">
            <div className="text-sm text-ui">
                {empty ? (
                    'Table is clear — a fresh combo is led'
                ) : (
                    <>
                        Pile to beat — laid by{' '}
                        <span className={`font-semibold ${owner === userPlayer ? 'text-primary' : 'text-ui-dark'}`}>
                            {owner}
                        </span>
                    </>
                )}
            </div>
            <div className="min-h-[3.85rem] flex items-center justify-center">
                {empty ? (
                    <span className="text-ui-light text-3xl">—</span>
                ) : (
                    <CardRow cards={combo} size="md" overlap={false} highlighted={combo} />
                )}
            </div>
        </div>
    );
};

export default ComboPile;
