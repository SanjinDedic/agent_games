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

    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        self.correct_letter = None

    def play_round(self):
        self.correct_letter = random.choice(string.ascii_lowercase)
        if self.verbose:
            print(f"The correct letter for this round is: {self.correct_letter}")

        for player in self.players:
            guess = player.make_decision(self.get_game_state())
            if guess == self.correct_letter:
                self.scores[player.name] = 1
                if self.verbose:
                    print(f"{player.name} guessed {guess} - Correct!")
            else:
                self.scores[player.name] = 0
                if self.verbose:
                    print(f"{player.name} guessed {guess} - Incorrect.")

    def get_game_state(self):
        return {"correct_letter": self.correct_letter}

    def play_game(self, custom_rewards=None):
        if self.verbose:
            print("Starting a new AlphaGuess game!")
        self.play_round()
        results = self.assign_points(self.scores, custom_rewards)
        if self.verbose:
            print("Game finished. Final scores:")
            for player, score in results["points"].items():
                print(f"{player}: {score}")
        return results

    def assign_points(self, scores, custom_rewards=None):
        return {"points": scores, "score_aggregate": scores}

def run_simulations(num_simulations, league, custom_rewards=None):
    return BaseGame.run_simulations(num_simulations, AlphaGuessGame, league, custom_rewards)