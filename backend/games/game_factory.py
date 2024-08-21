from games.greedy_pig.greedy_pig import GreedyPigGame
from games.forty_two.forty_two import FortyTwoGame
from games.alpha_guess.alpha_guess import AlphaGuessGame

class GameFactory:
    @staticmethod
    def get_game_class(game_name):
        if game_name == "greedy_pig":
            return GreedyPigGame
        elif game_name == "forty_two":
            return FortyTwoGame
        elif game_name == "alpha_guess":
            return AlphaGuessGame
        else:
            raise ValueError(f"Unknown game: {game_name}")