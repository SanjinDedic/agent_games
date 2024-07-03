import random
import os
import importlib.util
from abc import ABC, abstractmethod

class BaseGame(ABC):
    def __init__(self, league, verbose=False):
        self.verbose = verbose
        self.league = league
        self.players = self.get_all_player_classes_from_folder()
        self.scores = {player.name: 0 for player in self.players}

    def get_all_player_classes_from_folder(self):
        players = []
        current_dir = os.path.dirname(os.path.abspath(__file__))
        game_name = self.__class__.__module__.split('.')[-2]  # Get the game name from the module path
        league_directory = os.path.join(current_dir, game_name, self.league.folder)

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
            print(f"Total players found: {len(players)}")

        return players

    @abstractmethod
    def play_round(self):
        pass

    @abstractmethod
    def get_game_state(self):
        pass

    @abstractmethod
    def play_game(self):
        pass

    def reset(self):
        self.scores = {player.name: 0 for player in self.players}

    @staticmethod
    def run_simulations(num_simulations, game_class, league, custom_rewards=None):
        game = game_class(league)
        total_points = {player.name: 0 for player in game.players}
        total_wins = {player.name: 0 for player in game.players}

        for _ in range(num_simulations):
            game.reset()
            results = game.play_game(custom_rewards)
            
            for player, points in results["points"].items():
                total_points[player] += points
            
            winner = max(results["points"], key=results["points"].get)
            total_wins[winner] += 1

        return {
            "total_points": total_points,
            "total_wins": total_wins,
            "num_simulations": num_simulations
        }