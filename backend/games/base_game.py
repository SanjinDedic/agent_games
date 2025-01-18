import importlib
import logging
import aiohttp
from typing import List
from abc import ABC, abstractmethod

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
            game_name = self.__class__.__module__.split('.')[2]
            
            # Import the validation_players module for this specific game
            module_path = f"games.{game_name}.validation_players"
            validation_module = importlib.import_module(module_path)
            
            # Get the players list and create a copy
            if hasattr(validation_module, 'players'):
                # Only load if players list is empty
                if not self.players:
                    self.players = validation_module.players.copy()
                    self.scores = {str(player.name): 0 for player in self.players}
                logger.info(f"Successfully loaded {len(self.players)} validation players for {game_name}")
            else:
                logger.error(f"No players list found in validation_players module for {game_name}")
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

    async def get_all_player_classes_via_api(self, api_url: str = "http://localhost:8000", auth_token: str = None):
        """Fetch player code from API and create player instances"""
        try:
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            async with aiohttp.ClientSession() as session:
                # Get submissions for the league
                url = f"{api_url}/user/get-league-submissions/{self.league.id}"
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to fetch submissions: {await response.text()}")
                    
                    data = await response.json()
                    print("Here is the code data for teams: ", data)
                    submissions = data.get("data", {})
                    # TODO: Clear existing players before adding new ones
                    for team_name, code in submissions.items():
                        try:
                            self.add_player(code, team_name)
                        except Exception as e:
                            logger.error(f"Error creating player {team_name}: {str(e)}")

        except Exception as e:
            logger.error(f"Error fetching player code: {str(e)}")
            raise

    def add_player(self, code: str, name: str):
        """Create a player instance from code"""
        try:
            print(f"\nAttempting to create player '{name}'")
            # Create a module namespace with required imports
            namespace = {
                '__builtins__': __builtins__,
            }
            
            # Add necessary imports to namespace
            import games.prisoners_dilemma.player as player_module
            namespace['Player'] = player_module.Player
            
            print("Executing provided code...")
            # Execute the code in the prepared namespace
            exec(code, namespace)
            
            if "CustomPlayer" in namespace:
                print("CustomPlayer class found in namespace")
                player_class = namespace["CustomPlayer"]
                player = player_class()
                player.name = name
                print(f"Created player instance with name: {player.name}")
                
                self.players.append(player)
                self.scores[str(player.name)] = 0
                
                print(f"Added player to game. Current players: {[p.name for p in self.players]}")
                print(f"Updated scores dictionary: {self.scores}")
                
                return player
            else:
                print("No CustomPlayer class found in provided code")
                return None
                
        except Exception as e:
            print(f"Error creating player {name}: {str(e)}")
            return None

    def reset(self):
        """Reset scores but maintain the players list"""
        # Store current players
        current_players = self.players.copy()
        # Reset scores for all current players
        self.scores = {str(player.name): 0 for player in current_players}
        # Make sure we keep all current players
        self.players = current_players