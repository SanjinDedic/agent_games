import React from 'react';
import { useSelector } from 'react-redux';
import ResultsDisplay from '../Utilities/ResultsDisplay';
import Lineup4ResultsDisplay from './games/lineup4/Lineup4ResultsDisplay';

const GameResultsWrapper = (props) => {
    const currentLeague = useSelector((state) => state.leagues.currentLeague);

    // Determine which display component to use based on the game
    const getResultsDisplay = () => {
        if (currentLeague && currentLeague.game === 'lineup4') {
            return <Lineup4ResultsDisplay {...props} />;
        }

        // Default to the original ResultsDisplay for other games
        return <ResultsDisplay {...props} />;
    };

    return getResultsDisplay();
};

export default GameResultsWrapper;