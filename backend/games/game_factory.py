from backend.games.greedy_pig.greedy_pig import GreedyPigGame
from backend.games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame


class GameFactory:
    @staticmethod
    def get_game_class(game_name):
        if game_name == "greedy_pig":
            return GreedyPigGame
        elif game_name == "prisoners_dilemma":
            return PrisonersDilemmaGame
        elif game_name == "lineup4":
            from backend.games.lineup4.lineup4 import Lineup4Game

            return Lineup4Game
        else:
            raise ValueError(f"Unknown game: {game_name}")
