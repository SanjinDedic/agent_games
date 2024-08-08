from games.base_game import BaseGame
import random
import string

class AlphaGuessGame(BaseGame):
    starter_code = '''
from games.alpha_guess.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return random.choice(string.ascii_lowercase)
'''

    game_instructions = '''
<h1>AlphaGuess Game Instructions</h1>
<p>Guess the randomly selected letter (a-z). Correct guesses earn 1 point.</p>
'''

    def __init__(self, league):
        super().__init__(league)
        self.correct_letter = None

    def play_round(self):
        self.correct_letter = random.choice(string.ascii_lowercase)
        for player in self.players:
            if player.make_decision(self.get_game_state()) == self.correct_letter:
                self.scores[player.name] = 1
            else:
                self.scores[player.name] = 0

    def get_game_state(self):
        return {"correct_letter": self.correct_letter}

    def play_game(self, custom_rewards=None):
        self.play_round()
        return self.assign_points(self.scores, custom_rewards)

    def assign_points(self, scores, custom_rewards=None):
        return {"points": scores, "score_aggregate": scores}

def run_simulations(num_simulations, league, custom_rewards=None):
    return BaseGame.run_simulations(num_simulations, AlphaGuessGame, league, custom_rewards)