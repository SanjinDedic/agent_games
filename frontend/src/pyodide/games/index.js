/**
 * Manifest of game engines shipped to the in-browser (Pyodide) workers.
 *
 * The .py files under ./engine/ are VERBATIM copies of their backend
 * counterparts (backend/games/...): the workers write them onto Pyodide's
 * filesystem at the paths given here, so the engine imports
 * (`backend.games.<game>...`) resolve exactly as they do server-side.
 * Byte-equality with the backend originals is enforced by
 * backend/tests/unit/test_simulation_engine_copies.py — edit the backend
 * file and re-copy, never edit a copy directly.
 *
 * Two consumers with different scopes:
 * - validation.worker.js writes EVERY game in GAME_ENGINE_FILES (agent
 *   validation is in-browser for all games).
 * - simulation.worker.js writes only SIMULATION_GAMES (league simulation is
 *   enabled per game once its simulation UX has been tested; add a game
 *   there when it's ready).
 *
 * Adding a game = copy its three engine files here, add a GAME_ENGINE_FILES
 * entry, and add its paths to the parity test's ENGINE_COPIES list.
 */
import baseGame from './engine/base_game.py?raw';
import gameFactory from './engine/game_factory.py?raw';
import arenaChampionsGame from './engine/arena_champions/arena_champions.py?raw';
import arenaChampionsPlayer from './engine/arena_champions/player.py?raw';
import arenaChampionsValidation from './engine/arena_champions/validation_players.py?raw';
import breakthroughGame from './engine/breakthrough/breakthrough.py?raw';
import breakthroughPlayer from './engine/breakthrough/player.py?raw';
import breakthroughValidation from './engine/breakthrough/validation_players.py?raw';
import greedyPigGame from './engine/greedy_pig/greedy_pig.py?raw';
import greedyPigPlayer from './engine/greedy_pig/player.py?raw';
import greedyPigValidation from './engine/greedy_pig/validation_players.py?raw';
import heartsGame from './engine/hearts/hearts.py?raw';
import heartsPlayer from './engine/hearts/player.py?raw';
import heartsValidation from './engine/hearts/validation_players.py?raw';
import lineup4Game from './engine/lineup4/lineup4.py?raw';
import lineup4Player from './engine/lineup4/player.py?raw';
import lineup4Validation from './engine/lineup4/validation_players.py?raw';
import ohhellGame from './engine/ohhell/ohhell.py?raw';
import ohhellPlayer from './engine/ohhell/player.py?raw';
import ohhellValidation from './engine/ohhell/validation_players.py?raw';
import prisonersDilemmaGame from './engine/prisoners_dilemma/prisoners_dilemma.py?raw';
import prisonersDilemmaPlayer from './engine/prisoners_dilemma/player.py?raw';
import prisonersDilemmaValidation from './engine/prisoners_dilemma/validation_players.py?raw';
import thirteenGame from './engine/thirteen/thirteen.py?raw';
import thirteenPlayer from './engine/thirteen/player.py?raw';
import thirteenValidation from './engine/thirteen/validation_players.py?raw';

export const SHARED_FILES = {
  'backend/games/base_game.py': baseGame,
  'backend/games/game_factory.py': gameFactory,
};

const gameFiles = (name, game, player, validation) => ({
  files: {
    [`backend/games/${name}/${name}.py`]: game,
    [`backend/games/${name}/player.py`]: player,
    [`backend/games/${name}/validation_players.py`]: validation,
  },
});

export const GAME_ENGINE_FILES = {
  arena_champions: gameFiles(
    'arena_champions',
    arenaChampionsGame,
    arenaChampionsPlayer,
    arenaChampionsValidation
  ),
  breakthrough: gameFiles(
    'breakthrough',
    breakthroughGame,
    breakthroughPlayer,
    breakthroughValidation
  ),
  greedy_pig: gameFiles(
    'greedy_pig',
    greedyPigGame,
    greedyPigPlayer,
    greedyPigValidation
  ),
  hearts: gameFiles('hearts', heartsGame, heartsPlayer, heartsValidation),
  lineup4: gameFiles('lineup4', lineup4Game, lineup4Player, lineup4Validation),
  ohhell: gameFiles('ohhell', ohhellGame, ohhellPlayer, ohhellValidation),
  prisoners_dilemma: gameFiles(
    'prisoners_dilemma',
    prisonersDilemmaGame,
    prisonersDilemmaPlayer,
    prisonersDilemmaValidation
  ),
  thirteen: gameFiles(
    'thirteen',
    thirteenGame,
    thirteenPlayer,
    thirteenValidation
  ),
};

export const SIMULATION_GAMES = {
  greedy_pig: GAME_ENGINE_FILES.greedy_pig,
};

export const isSimulationSupported = (gameName) =>
  gameName in SIMULATION_GAMES;

export const isValidationSupported = (gameName) =>
  gameName in GAME_ENGINE_FILES;
