from backend.games.greedy_pig.greedy_pig import GreedyPigGame
from backend.games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame


class GameFactory:
    @staticmethod
    def get_game_class(game_name):
        if game_name == "greedy_pig":
            return GreedyPigGame
        elif game_name == "prisoners_dilemma":
            return PrisonersDilemmaGame
        elif game_name == "connect4":
            from backend.games.connect4.connect4 import Connect4Game

            return Connect4Game
        else:
            raise ValueError(f"Unknown game: {game_name}")
