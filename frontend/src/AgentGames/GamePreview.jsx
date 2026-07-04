import React from 'react';
import { useParams } from 'react-router-dom';
import { getGame, gamesList } from './Feedback/games';
import DefaultResultsDisplay from './Shared/Utilities/ResultsDisplay';

// Dev harness: renders a game's Feedback and ResultsDisplay components from
// the sample data bundled in its manifest — no backend or league required.
// e.g. /GamePreview/hearts
const GamePreview = () => {
    const { gameName } = useParams();
    const game = getGame(gameName);

    if (!game) {
        return (
            <div className="max-w-3xl mx-auto p-8 text-ui-dark">
                <h1 className="text-2xl font-bold mb-4">Unknown game “{gameName}”</h1>
                <p>Available games: {gamesList.map((g) => g.name).join(', ')}</p>
            </div>
        );
    }

    if (!game.sampleFeedback && !game.sampleResults) {
        return (
            <div className="max-w-3xl mx-auto p-8 text-ui-dark">
                <h1 className="text-2xl font-bold mb-4">{game.displayName}</h1>
                <p>
                    No sample data in this game's manifest. Add <code>sampleFeedback</code> /{' '}
                    <code>sampleResults</code> to its <code>index.jsx</code> to preview it here.
                </p>
            </div>
        );
    }

    const Results = game.ResultsDisplay || DefaultResultsDisplay;

    return (
        <div className="max-w-5xl mx-auto p-4 md:p-8 space-y-10">
            <div>
                <h1 className="text-3xl font-bold text-ui-dark">{game.displayName} — preview</h1>
                <p className="text-ui">Rendered from bundled sample data (no backend).</p>
            </div>

            {game.sampleResults && (
                <section>
                    <h2 className="text-xl font-semibold text-ui-dark mb-3">Simulation rankings</h2>
                    <Results data={game.sampleResults} tablevisible={true} data_message="" highlight={false} />
                </section>
            )}

            {game.sampleFeedback && (
                <section>
                    <h2 className="text-xl font-semibold text-ui-dark mb-3">Single game feedback</h2>
                    <game.Feedback feedback={game.sampleFeedback} />
                </section>
            )}
        </div>
    );
};

export default GamePreview;
