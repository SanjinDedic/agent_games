/**
 * Manifest of games runnable by the in-browser (Pyodide) simulation worker.
 *
 * The .py files under ./engine/ are VERBATIM copies of their backend
 * counterparts (backend/games/...): the simulation worker writes them onto
 * Pyodide's filesystem at the paths given here, so the engine imports
 * (`backend.games.<game>...`) resolve exactly as they do server-side.
 * Byte-equality with the backend originals is enforced by
 * backend/tests/unit/test_simulation_engine_copies.py — edit the backend
 * file and re-copy, never edit a copy directly.
 *
 * Porting another game = copy its engine files here, add an entry to
 * SIMULATION_GAMES, and add its paths to the parity test.
 */
import baseGame from './engine/base_game.py?raw';
import gameFactory from './engine/game_factory.py?raw';
import greedyPigGame from './engine/greedy_pig/greedy_pig.py?raw';
import greedyPigPlayer from './engine/greedy_pig/player.py?raw';
import greedyPigValidation from './engine/greedy_pig/validation_players.py?raw';

export const SHARED_FILES = {
  'backend/games/base_game.py': baseGame,
  'backend/games/game_factory.py': gameFactory,
};

export const SIMULATION_GAMES = {
  greedy_pig: {
    files: {
      'backend/games/greedy_pig/greedy_pig.py': greedyPigGame,
      'backend/games/greedy_pig/player.py': greedyPigPlayer,
      'backend/games/greedy_pig/validation_players.py': greedyPigValidation,
    },
  },
};

export const isSimulationSupported = (gameName) =>
  gameName in SIMULATION_GAMES;
