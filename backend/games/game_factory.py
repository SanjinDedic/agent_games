from backend.games.greedy_pig.greedy_pig import GreedyPigGame
from backend.games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame


class GameFactory:
    @staticmethod
    def get_game_class(game_name):
        if game_name == "greedy_pig":
            return GreedyPigGame
        elif game_name == "prisoners_dilemma":
            return PrisonersDilemmaGame
        elif game_name == "alpha_guess":
            from backend.games.alpha_guess.alpha_guess import AlphaGuessGame

            return AlphaGuessGame

        else:
            raise ValueError(f"Unknown game: {game_name}")
