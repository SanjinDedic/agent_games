import React from 'react';
import { useSelector } from 'react-redux';
import ResultsDisplay from '../Shared/Utilities/ResultsDisplay';
import { getGame } from './games';

const GameResultsWrapper = (props) => {
    const currentLeague = useSelector((state) => state.leagues.currentLeague);
    const game = currentLeague ? getGame(currentLeague.game) : null;
    const Display = game?.ResultsDisplay || ResultsDisplay;
    return <Display {...props} />;
};

export default GameResultsWrapper;
