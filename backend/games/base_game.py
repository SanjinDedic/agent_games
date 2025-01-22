import importlib
import logging
from abc import ABC

import httpx

from backend.config import DOCKER_API_URL, SERVICE_TOKEN

logger = logging.getLogger(__name__)


class BaseGame(ABC):
    starter_code = """
    # This is a base starter code.
    # Each game should override this with its specific starter code.
    """

    game_instructions = """
    <h1>Base Game Instructions</h1>
    <p>These are generic game instructions. Each game should provide its own specific instructions.</p>
    """

    def __init__(self, league, verbose=False):
        self.verbose = verbose
        self.league = league
        self.players = []
        self.scores = {}
        # Load validation players during initialization
        self.load_validation_players()

    def load_validation_players(self):
        """
        Load validation players from the game's validation_players module.
        Each game must have a validation_players.py file with a 'players' list.
        """
        try:
            # Get the name of the game from the class name
            game_name = self.__class__.__module__.split(".")[2]

            # Import the validation_players module for this specific game
            module_path = f"games.{game_name}.validation_players"
            validation_module = importlib.import_module(module_path)

            # Get the players list and create a copy
            if hasattr(validation_module, "players"):
                # Only load if players list is empty
                if not self.players:
                    self.players = validation_module.players.copy()
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

    def __init__(self, league, verbose=False):
        """Initialize with validation players by default"""
        self.verbose = verbose
        self.league = league
        self.players = []
        self.scores = {}
        # Load validation players by default for new leagues
        self.load_validation_players()

    async def get_all_player_classes_via_api(
        self, api_url: str = "http://localhost:8000", auth_token: str = None
    ):
        """Fetch player code from API and create player instances"""
        try:
            token = auth_token or SERVICE_TOKEN
            headers = {"Authorization": f"Bearer {token}"}

            base_url = api_url or DOCKER_API_URL
            logger.info(f"Using API URL: {base_url}")
            url = f"{base_url}/user/get-league-submissions/{self.league.id}"
            logger.info(f"Attempting to fetch submissions from: {url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)

                if response.status_code != 200:
                    logger.error(
                        f"Failed to fetch submissions. Status: {response.status_code}, Error: {response.text}"
                    )
                    raise Exception(f"Failed to fetch submissions: {response.text}")

                data = response.json()
                logger.info("Received API response")
                submissions = data.get("data", {})

                if submissions:
                    # Only clear players if we have submissions to replace them with
                    logger.info("Found league submissions, clearing validation players")
                    self.players = []
                    self.scores = {}

                    # Add submitted players
                    for team_name, code in submissions.items():
                        try:
                            logger.info(f"Creating player for team: {team_name}")
                            player = self.add_player(code, team_name)
                            if player:
                                logger.info(
                                    f"Successfully added player for team: {team_name}"
                                )
                        except Exception as e:
                            logger.error(f"Error creating player {team_name}: {str(e)}")

                    logger.info(f"Total league players loaded: {len(self.players)}")
                    logger.info(f"Player names: {[p.name for p in self.players]}")
                else:
                    logger.info(
                        "No league submissions found, keeping validation players"
                    )

        except Exception as e:
            logger.error(f"Error fetching player code: {str(e)}")
            logger.info("Keeping existing validation players due to error")

    def add_player(self, code: str, name: str):
        """Create a player instance from code"""
        try:
            # Get the game name from the class name for dynamic imports
            game_name = self.__class__.__module__.split(".")[2]

            # Create a module namespace with required imports
            namespace = {
                "__builtins__": __builtins__,
            }

            # Dynamically import the correct player module based on game
            player_module = importlib.import_module(f"games.{game_name}.player")
            namespace["Player"] = player_module.Player

            # Execute the code in the prepared namespace
            exec(code, namespace)

            if "CustomPlayer" not in namespace:
                logger.error(f"No CustomPlayer class found in code for {name}")
                return None

            player_class = namespace["CustomPlayer"]

            # Verify the player class inherits from the correct base
            if not issubclass(player_class, player_module.Player):
                logger.error(
                    f"CustomPlayer for {name} does not inherit from correct Player base class"
                )
                return None

            player = player_class()
            player.name = name

            self.players.append(player)
            self.scores[str(player.name)] = 0

            return player

        except Exception as e:
            logger.error(f"Error creating player {name}: {str(e)}", exc_info=True)
            return None

    def reset(self):
        """Reset scores but maintain the players list"""
        # Store current players
        current_players = self.players.copy()
        # Reset scores for all current players
        self.scores = {str(player.name): 0 for player in current_players}
        # Make sure we keep all current players
        self.players = current_players
