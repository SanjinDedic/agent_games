import copy
import importlib
import logging
import traceback
from abc import ABC

logger = logging.getLogger(__name__)


class PlayerConstructionError(Exception):
    """A submission could not be turned into a live player instance.

    Raised by add_player. ``traceback_str`` carries the formatted traceback of
    the underlying exception when there was one (exec of the submission or
    CustomPlayer.__init__ failing); it is None for structural problems (no
    CustomPlayer class, wrong base class) where a traceback adds nothing.
    """

    def __init__(self, message, traceback_str=None):
        super().__init__(message)
        self.traceback_str = traceback_str


class BaseGame(ABC):
    starter_code = """
    # This is a base starter code.
    # Each game should override this with its specific starter code.
    """

    game_instructions = """
    <h1>Base Game Instructions</h1>
    <p>These are generic game instructions. Each game should provide its own specific instructions.</p>
    """

    # None → game does not accept custom rewards; UI hides the input.
    # dict → schema descriptor consumed by the frontend:
    #   {
    #     "kind": "placement" | "matrix",
    #     "length": int,                  # required entry count
    #     "labels": [str, ...] | None,    # optional per-cell labels (matrix games)
    #     "default": [number, ...],       # values shown when user has not customised
    #   }
    reward_schema = None

    # Markdown shown next to the custom rewards input.
    reward_instructions = ""

    # How many simulation passes a submission validation runs for this game.
    # Each game overrides this with a value benchmarked (in the worker image)
    # so the whole validation load — feedback game + simulations — stays under
    # one second. Games whose run_simulations fans out into many sub-games per
    # pass (hearts, ohhell, thirteen) need only a handful of passes.
    validation_simulations = 20

    def __init__(self, league, verbose=False):
        self.verbose = verbose
        self.league = league
        self.players = []
        self.scores = {}
        self.game_feedback = []  # Can be overridden by games to be a dict if needed
        self.player_feedback = {}
        self.load_validation_players()

    def add_feedback(self, message):
        """Add a feedback message if verbose mode is on"""
        if self.verbose:
            if isinstance(self.game_feedback, list):
                self.game_feedback.append(message)
            elif isinstance(self.game_feedback, dict):
                # For games using dictionary feedback structure
                if "moves" in self.game_feedback:
                    self.game_feedback["moves"].append(message)
                elif "matches" in self.game_feedback:
                    self.game_feedback["matches"].append(message)
            elif isinstance(self.game_feedback, str):
                # For games using string/markdown feedback
                self.game_feedback += str(message) + "\n"

    def load_validation_players(self):
        """
        Load validation players from the game's validation_players module.
        Each game must have a validation_players.py file with a 'players' list.
        """
        try:
            # Get the name of the game from the class name
            game_name = self.__class__.__module__.split(".")[2]

            # Import the validation_players module for this specific game
            module_path = f"backend.games.{game_name}.validation_players"
            validation_module = importlib.import_module(module_path)

            # Get the players list and create a copy
            if hasattr(validation_module, "players"):
                # Only load if players list is empty
                if not self.players:
                    self.players = copy.deepcopy(validation_module.players)
                    self.scores = {str(player.name): 0 for player in self.players}
                logger.info(
                    f"Successfully loaded {len(self.players)} validation players for {game_name}"
                )
            else:
                logger.error(
                    f"No players list found in validation_players module for {game_name}"
                )
                if not self.players:
                    self.players = []
                    self.scores = {}

        except ImportError as e:
            logger.error(f"Could not find validation_players.py for game: {str(e)}")
            if not self.players:
                self.players = []
                self.scores = {}
        except Exception as e:
            logger.error(f"Error loading validation players: {str(e)}")
            if not self.players:
                self.players = []
                self.scores = {}

    def get_player_strategies(self):
        """Map player name -> strategy for players that declare one.

        Validation players carry a `strategy` class attribute; user-submitted
        players don't, so the map naturally covers only the built-in bots.
        """
        return {
            str(player.name): player.strategy
            for player in self.players
            if getattr(player, "strategy", None)
        }

    def add_player(self, code: str, name: str):
        """Create a player instance from code.

        Raises PlayerConstructionError when the code cannot be turned into a
        player; its ``traceback_str`` (when set) is surfaced to the student
        via the AI hint context.
        """
        try:
            # Get the game name from the class name for dynamic imports
            game_name = self.__class__.__module__.split(".")[2]

            logger.info(f"Adding player for {name} with game {game_name}")

            # Create a module namespace with required imports
            namespace = {
                "__builtins__": __builtins__,
            }

            # Dynamically import the correct player module based on game using backend prefix
            logger.info(f"Importing player module for {game_name}")
            player_module = importlib.import_module(f"backend.games.{game_name}.player")
            namespace["Player"] = player_module.Player

            # Need to modify the code to use the correct import path too
            modified_code = code.replace(
                f"from games.{game_name}.player",
                f"from backend.games.{game_name}.player",
            )

            logger.info("Executing submitted code")
            # Execute the modified code in the prepared namespace
            exec(modified_code, namespace)

            if "CustomPlayer" not in namespace:
                logger.error(f"No CustomPlayer class found in code for {name}")
                raise PlayerConstructionError(
                    "No CustomPlayer class found in the submitted code"
                )

            player_class = namespace["CustomPlayer"]

            # Verify the player class inherits from the correct base
            if not issubclass(player_class, player_module.Player):
                logger.error(
                    f"CustomPlayer for {name} does not inherit from correct Player base class"
                )
                raise PlayerConstructionError(
                    "CustomPlayer does not inherit from the game's Player base class"
                )

            player = player_class()
            player.name = name

            logger.info(f"Successfully created player instance for {name}")

            self.players.append(player)
            self.scores[str(player.name)] = 0

            logger.info(
                f"Current players after adding {name}: {[p.name for p in self.players]}"
            )

            return player

        except PlayerConstructionError:
            raise
        except Exception as e:
            logger.error(f"Error creating player {name}: {str(e)}", exc_info=True)
            raise PlayerConstructionError(
                f"{type(e).__name__}: {e}", traceback_str=traceback.format_exc()
            ) from e

    def run_single_game_with_feedback(self, custom_rewards=None):
        """Run a single game with feedback"""
        self.verbose = True  # Enable feedback for this run
        results = self.play_game(custom_rewards)
        return {
            "results": results,
            "feedback": self.game_feedback,
            "player_feedback": self.player_feedback,
        }

    def reset(self):
        """Reset scores but maintain the players list"""
        # Store current players
        current_players = self.players.copy()
        # Reset scores for all current players
        self.scores = {str(player.name): 0 for player in current_players}
        # Make sure we keep all current players
        self.players = current_players
        # Reset feedback - maintain the same type as initialized
        if isinstance(self.game_feedback, list):
            self.game_feedback = []
        elif isinstance(self.game_feedback, dict):
            game_name = self.__class__.__module__.split(".")[2]
            self.game_feedback = {"game": game_name, "moves": []}
        elif isinstance(self.game_feedback, str):
            self.game_feedback = ""
        self.player_feedback = {}
