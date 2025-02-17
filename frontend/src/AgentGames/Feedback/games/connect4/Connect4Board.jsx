import React from 'react';

const Connect4Board = ({ boardState }) => {
    const getCellContent = (cell) => {
        if (!cell) return null;
        return cell === 'X' ?
            <div className="w-12 h-12 rounded-full bg-primary shadow-md flex items-center justify-center">
                <span className="text-white font-bold text-2xl">{cell}</span>
            </div> :
            <div className="w-12 h-12 rounded-full bg-danger shadow-md flex items-center justify-center">
                <span className="text-white font-bold text-2xl">{cell}</span>
            </div>;
    };

    // Board layout: columns 1-7, rows A-F (bottom to top)
    const rows = ['F', 'E', 'D', 'C', 'B', 'A'];
    const cols = ['1', '2', '3', '4', '5', '6', '7'];

    return (
        <div className="max-w-[650px] bg-ui-lighter p-6 rounded-lg mx-auto">
            <div className="grid grid-cols-[auto_repeat(7,_1fr)] gap-1">
                {/* Empty top-left corner */}
                <div className="w-8" />

                {/* Column headers */}
                {cols.map(col => (
                    <div key={col} className="flex justify-center items-center h-8 text-lg font-bold text-ui-dark -ml-6">
                        {col}
                    </div>
                ))}

                {/* Board rows with row labels */}
                {rows.map(row => (
                    <React.Fragment key={row}>
                        {/* Row label */}
                        <div className="flex items-center justify-center w-8 text-lg font-bold text-ui-dark">
                            {row}
                        </div>

                        {/* Board cells */}
                        {cols.map(col => {
                            const position = `${col}${row}`;
                            return (
                                <div
                                    key={position}
                                    className="w-14 h-14 bg-white rounded-lg flex items-center justify-center border-2 border-ui-light"
                                >
                                    {getCellContent(boardState[position])}
                                </div>
                            );
                        })}
                    </React.Fragment>
                ))}
            </div>
        </div>
    );
};

export default Connect4Board;