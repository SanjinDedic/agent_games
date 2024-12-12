import importlib.util
import os
import random
from abc import ABC, abstractmethod

from config import ROOT_DIR


class BaseGame(ABC):
    starter_code = '''
# This is a base starter code.
# Each game should override this with its specific starter code.
'''

    game_instructions = '''
<h1>Base Game Instructions</h1>

<p>These are generic game instructions. Each game should provide its own specific instructions.</p>
'''

    def __init__(self, league, verbose=False):
        self.verbose = verbose
        self.league = league
        self.players = self.get_all_player_classes_from_folder()
        self.scores = {player.name: 0 for player in self.players}

    def get_all_player_classes_from_folder(self):
        players = []
        league_directory = os.path.join(ROOT_DIR, "games", self.league.game, self.league.folder)

        if self.verbose:
            print(f"Searching for player classes in: {league_directory}")

        if not os.path.exists(league_directory):
            print(f"The folder '{league_directory}' does not exist.")
            return players

        for item in os.listdir(league_directory):
            if item.endswith(".py"):
                module_name = item[:-3]
                module_path = os.path.join(league_directory, item)

                if self.verbose:
                    print(f"Found Python file: {module_path}")

                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if hasattr(module, "CustomPlayer"):
                    player_class = getattr(module, "CustomPlayer")
                    player = player_class()
                    player.name = module_name
                    players.append(player)
                    if self.verbose:
                        print(f"Added player: {player.name}")

        if self.verbose:
            print(f"Total players found: {len(players)}, {players}")

        return players

    @abstractmethod
    def get_game_state(self):
        pass

    @abstractmethod
    def play_game(self):
        pass

    def reset(self):
        self.scores = {player.name: 0 for player in self.players}

    @classmethod
    def run_simulations(cls, num_simulations, league, custom_rewards=None):
        pass
    
    @classmethod
    def get_starter_code(cls):
        return cls.starter_code

    @classmethod
    def get_game_instructions(cls):
        return cls.game_instructions