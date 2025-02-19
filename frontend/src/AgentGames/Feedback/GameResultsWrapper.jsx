import React from 'react';
import { useSelector } from 'react-redux';
import ResultsDisplay from '../Utilities/ResultsDisplay';
import Connect4ResultsDisplay from './games/connect4/Connect4ResultsDisplay';

const GameResultsWrapper = (props) => {
    const currentLeague = useSelector((state) => state.leagues.currentLeague);

    // Determine which display component to use based on the game
    const getResultsDisplay = () => {
        if (currentLeague && currentLeague.game === 'connect4') {
            return <Connect4ResultsDisplay {...props} />;
        }

        // Default to the original ResultsDisplay for other games
        return <ResultsDisplay {...props} />;
    };

    return getResultsDisplay();
};

export default GameResultsWrapper;