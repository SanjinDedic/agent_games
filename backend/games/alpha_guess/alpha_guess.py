from games.base_game import BaseGame
import random
import string

class AlphaGuessGame(BaseGame):
    starter_code = '''
from games.alpha_guess.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return random.choice('abcdefghijklmnopqrstuvwxyz')
'''

    game_instructions = '''
<h1>Alpha Guess Game Instructions</h1>

<p>Welcome to the Alpha Guess game! Your task is to implement the <code>make_decision</code> method in the <code>CustomPlayer</code> class.</p>

<h2>1. Game Objective</h2>
<p>Guess a letter as close as possible to a randomly chosen target letter.</p>

<h2>2. Your Task</h2>
<p>Implement the <code>make_decision</code> method to return a single lowercase letter from 'a' to 'z'.</p>

<h2>3. Scoring</h2>
<p>Points are awarded based on how close your guess is to the target letter. The closer your guess, the more points you receive.</p>

<h2>4. Implementation Example</h2>
<pre><code>
def make_decision(self, game_state):
    return random.choice('abcdefghijklmnopqrstuvwxyz')
</code></pre>

<p>Good luck and have fun!</p>
'''

    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        self.feedback = []

    def add_feedback(self, message):
        if self.verbose:
            self.feedback.append(message)

    def play_game(self, custom_rewards=None):
        self.add_feedback("# Alpha Guess Game")
        self.add_feedback("\n## Players:")
        for player in self.players:
            self.add_feedback(f"  - {player.name}")
        
        target_letter = random.choice(string.ascii_lowercase)
        self.add_feedback(f"\nTarget letter: {target_letter}")

        points = {player.name: 0 for player in self.players}
        for player in self.players:
            guess = player.make_decision(self.get_game_state(player.name))
            distance = abs(ord(guess) - ord(target_letter))
            points[player.name] = 26 - distance  # Max score is 26 (correct guess), min is 0
            self.add_feedback(f"{player.name} guessed: {guess}, score: {points[player.name]}")

        return {"points": points, "score_aggregate": points}

    def get_game_state(self, player_name):
        return {
            "player_name": player_name,
            "scores": self.scores
        }

    @classmethod
    def run_single_game_with_feedback(cls, league, custom_rewards=None):
        game = cls(league, verbose=True)
        results = game.play_game()
        feedback = "\n".join(game.feedback)
        return {
            "results": results,
            "feedback": feedback
        }

    @classmethod
    def run_simulations(cls, num_simulations, league, custom_rewards=None):
        game = cls(league)
        total_points = {player.name: 0 for player in game.players}
        total_wins = {player.name: 0 for player in game.players}

        for _ in range(num_simulations):
            game.reset()
            results = game.play_game()

            for player, points in results["points"].items():
                total_points[player] += points

            if results["points"]:
                winner = max(results["points"], key=results["points"].get)
                total_wins[winner] += 1

        return {
            "total_points": total_points,
            "total_wins": total_wins,
            "num_simulations": num_simulations
        }

    def reset(self):
        super().reset()
        self.feedback = []

    @classmethod
    def run_simulations(cls, num_simulations, league, custom_rewards=None):
        game = cls(league)
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
            "num_simulations": num_simulations,
            "table": {
                "total_wins": total_wins
            }
        }