import React, { useState, useEffect } from 'react';
import Connect4Board from './Connect4Board';
import Connect4PlayerFeedback from './Connect4PlayerFeedback';

const Connect4Feedback = ({ feedback }) => {
    const [selectedPlayer, setSelectedPlayer] = useState('all');
    const [selectedMatch, setSelectedMatch] = useState(0);
    const [currentMoveIndex, setCurrentMoveIndex] = useState(0);
    const [currentBoard, setCurrentBoard] = useState({});
    const [gameOver, setGameOver] = useState(false);
    const [filteredMatches, setFilteredMatches] = useState([]);
    const [players, setPlayers] = useState([]);

    useEffect(() => {
        if (feedback?.matches) {
            const uniquePlayers = new Set();
            feedback.matches.forEach(match => {
                uniquePlayers.add(match.player1);
                uniquePlayers.add(match.player2);
            });
            setPlayers(Array.from(uniquePlayers).sort());
            setFilteredMatches(feedback.matches);

            if (feedback.matches.length > 0 && feedback.matches[0].moves.length > 0) {
                setCurrentBoard(feedback.matches[0].moves[0].board_state);
            }
        }
    }, [feedback]);

    useEffect(() => {
        if (feedback?.matches) {
            const matches = selectedPlayer === 'all'
                ? feedback.matches
                : feedback.matches.filter(match =>
                    match.player1 === selectedPlayer || match.player2 === selectedPlayer
                );

            setFilteredMatches(matches);
            setSelectedMatch(0);
            setCurrentMoveIndex(0);
            setGameOver(false);
            if (matches.length > 0 && matches[0].moves.length > 0) {
                setCurrentBoard(matches[0].moves[0].board_state);
            }
        }
    }, [selectedPlayer, feedback]);

    if (!feedback?.matches || feedback.matches.length === 0) {
        return <div className="text-ui-dark">No game data available</div>;
    }

    if (filteredMatches.length === 0) {
        return <div className="text-ui-dark">No matches found for the selected filters</div>;
    }

    const currentMatchData = filteredMatches[selectedMatch] || filteredMatches[0];
    if (!currentMatchData) {
        return <div className="text-ui-dark">Match data not available</div>;
    }

    const moves = currentMatchData.moves || [];
    const winner = currentMatchData.winner;
    const final_board = currentMatchData.final_board;
    const player1 = currentMatchData.player1;
    const player2 = currentMatchData.player2;

    const handlePlayerChange = (e) => {
        setSelectedPlayer(e.target.value);
    };

    const handleMatchChange = (e) => {
        const matchIndex = parseInt(e.target.value);
        setSelectedMatch(matchIndex);
        setCurrentMoveIndex(0);
        setGameOver(false);
        if (filteredMatches[matchIndex]?.moves?.length > 0) {
            setCurrentBoard(filteredMatches[matchIndex].moves[0].board_state);
        }
    };

    const handleNext = () => {
        if (currentMoveIndex < moves.length) {
            const nextIndex = currentMoveIndex + 1;
            setCurrentMoveIndex(nextIndex);

            if (nextIndex === moves.length) {
                setGameOver(true);
                setCurrentBoard(final_board);
            } else {
                setCurrentBoard(moves[nextIndex].board_state);
            }
        }
    };

    const handlePrevious = () => {
        if (currentMoveIndex > 0) {
            const prevIndex = currentMoveIndex - 1;
            setCurrentMoveIndex(prevIndex);
            setGameOver(false);
            setCurrentBoard(moves[prevIndex].board_state);
        }
    };

    const getCurrentMove = () => {
        if (gameOver || !moves[currentMoveIndex]) return null;
        return moves[currentMoveIndex];
    };

    const getPlayerColor = (match, playerNumber) => {
        if (!match) return '';
        const player = playerNumber === 1 ? match.player1 : match.player2;
        const firstMove = match.moves?.[0];
        if (firstMove?.player === player) {
            return firstMove.symbol === 'X' ? 'text-primary' : 'text-danger';
        }
        return firstMove?.symbol === 'X' ? 'text-danger' : 'text-primary';
    };

    return (
        <div className="bg-white p-6 rounded-lg shadow-lg">
            <div className="mb-6 space-y-4">
                <div>
                    <label className="block text-ui-dark font-medium mb-2">Select Player</label>
                    <select
                        value={selectedPlayer}
                        onChange={handlePlayerChange}
                        className="w-full p-3 border border-ui-light rounded-lg bg-white text-ui-dark"
                    >
                        <option value="all">All Players</option>
                        {players.map(player => (
                            <option key={player} value={player}>
                                {player}
                            </option>
                        ))}
                    </select>
                </div>

                <div>
                    <label className="block text-ui-dark font-medium mb-2">Select Match</label>
                    <select
                        value={selectedMatch}
                        onChange={handleMatchChange}
                        className="w-full p-3 border border-ui-light rounded-lg bg-white text-ui-dark"
                    >
                        {filteredMatches.map((match, index) => (
                            <option key={index} value={index}>
                                {match.player1} vs {match.player2}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="mb-6 text-center">
                <h2 className="text-xl font-bold mb-2 flex items-center justify-center gap-2">
                    <span className={getPlayerColor(currentMatchData, 1)}>{player1}</span>
                    <span className="text-ui-dark">vs</span>
                    <span className={getPlayerColor(currentMatchData, 2)}>{player2}</span>
                </h2>
                <div className="text-lg">
                    {gameOver ? (
                        <div className="text-success font-semibold">
                            Winner: {winner}
                        </div>
                    ) : (
                        getCurrentMove() && (
                            <div className="text-ui">
                                Move {currentMoveIndex + 1}: Player {getCurrentMove().player} ({getCurrentMove().symbol})
                                {getCurrentMove().position && ` → ${getCurrentMove().position}`}
                            </div>
                        )
                    )}
                </div>
            </div>

            <Connect4Board boardState={currentBoard} />



            <div className="flex justify-center items-center gap-6 mt-6">
                <button
                    onClick={handlePrevious}
                    disabled={currentMoveIndex === 0}
                    className="px-6 py-3 text-lg rounded-lg bg-ui-lighter hover:bg-ui-light disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    ←
                </button>
                <span className="text-lg text-ui-dark">
                    {gameOver ? 'Game Over' : `Move ${currentMoveIndex + 1} of ${moves.length}`}
                </span>
                <button
                    onClick={handleNext}
                    disabled={gameOver}
                    className="px-6 py-3 text-lg rounded-lg bg-ui-lighter hover:bg-ui-light disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    →
                </button>
            </div>

            {/* Display move feedback using the separate component */}
            {getCurrentMove() && (
                <Connect4PlayerFeedback currentMove={getCurrentMove()} />
            )}
        </div>
    );
};

export default Connect4Feedback;