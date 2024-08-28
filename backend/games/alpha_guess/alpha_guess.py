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

    def __init__(self, league, verbose=False, custom_rewards=None):
        super().__init__(league, verbose)
        self.correct_letter = None
        self.custom_rewards = custom_rewards or [1, 0]  # Winner gets 1 point, others 0
        self.feedback = []

    def add_feedback(self, message):
        if self.verbose:
            self.feedback.append(message)

    def play_round(self):
        self.correct_letter = random.choice(string.ascii_lowercase)
        self.add_feedback(f"\n## Round")
        self.add_feedback(f"The correct letter for this round is: {self.correct_letter}")

        for player in self.players:
            guess = player.make_decision(self.get_game_state())
            if guess == self.correct_letter:
                self.scores[player.name] = 1
                self.add_feedback(f"- {player.name} guessed {guess} - Correct!")
            else:
                self.scores[player.name] = 0
                self.add_feedback(f"- {player.name} guessed {guess} - Incorrect.")

    def get_game_state(self):
        return {"correct_letter": self.correct_letter}

    def play_game(self, custom_rewards=None):
        self.add_feedback("# AlphaGuess Game")
        self.add_feedback("\n## Player order:")
        for i, player in enumerate(self.players, 1):
            self.add_feedback(f"{i}. {player.name}")

        self.add_feedback("\n## Game Play")
        self.play_round()
        
        results = self.assign_points(self.scores, custom_rewards)
        
        self.add_feedback("\n## Final Scores")
        for player, score in self.scores.items():
            self.add_feedback(f"- {player}: {score}")
        
        self.add_feedback("\n## Points Awarded")
        for player, points in results["points"].items():
            self.add_feedback(f"- {player}: {points} points")

        return results

    def assign_points(self, scores, custom_rewards=None):
        rewards = custom_rewards or self.custom_rewards
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        points = {}
        last_score = None
        last_reward = 0
        reward_index = 0

        for i, (player, score) in enumerate(sorted_scores):
            if score != last_score:
                if reward_index < len(rewards):
                    last_reward = rewards[reward_index]
                    reward_index += 1
                else:
                    last_reward = 0

            points[player] = last_reward
            last_score = score

        return {"points": points, "score_aggregate": scores}

    def reset(self):
        super().reset()
        self.correct_letter = None
        self.feedback = []

    @classmethod
    def run_single_game_with_feedback(cls, league, custom_rewards=None):
        game = cls(league, verbose=True, custom_rewards=custom_rewards)
        results = game.play_game(custom_rewards)
        feedback = "\n".join(game.feedback)
        return {
            "results": results,
            "feedback": feedback
        }