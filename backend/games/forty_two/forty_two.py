from games.base_game import BaseGame
import random

class FortyTwoGame(BaseGame):
    starter_code = '''
from games.forty_two.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        # Your code here
        return 'hit'  # or 'stand'
'''

    game_instructions = '''
<h1>Forty-Two Game Instructions</h1>

<p>Welcome to the Forty-Two game! Your task is to implement the <code>make_decision</code> method in the <code>CustomPlayer</code> class.</p>

<h2>1. Game Objective</h2>
<p>Get as close to 42 points as possible without going over.</p>

<h2>2. Your Task</h2>
<p>Implement the <code>make_decision</code> method to decide whether to 'hit' (draw another card) or 'stand' (keep your current hand).</p>

<h2>3. Available Information</h2>
<p>The <code>game_state</code> parameter provides you with the following information:</p>
<ul>
    <li><code>player_name</code>: Your player's name</li>
    <li><code>current_hand</code>: The current sum of your hand</li>
    <li><code>scores</code>: Dictionary of each player's total score from previous rounds</li>
</ul>

<h2>4. Implementation Example</h2>
<pre><code>
def make_decision(self, game_state):
    current_hand = game_state["current_hand"]

    if current_hand < 30:
        return 'hit'
    elif current_hand < 36:
        return 'hit' if random.random() < 0.5 else 'stand'
    else:
        return 'stand'
</code></pre>

<h2>5. Strategy Tips</h2>
<ul>
    <li>Remember, going over 42 results in a score of 0 for the round</li>
    <li>Consider the probability of busting when deciding to hit</li>
    <li>You can use the <code>scores</code> dictionary to adapt your strategy based on other players' performance</li>
    <li>Balance aggression (trying to get close to 42) with caution (avoiding busting)</li>
</ul>

<p>Good luck and have fun!</p>
'''

    def __init__(self, league, verbose=False, custom_rewards=None):
        super().__init__(league, verbose)
        self.custom_rewards = custom_rewards or [10, 8, 6, 4, 3, 2, 1]
        self.feedback = []

    def add_feedback(self, message):
        if self.verbose:
            self.feedback.append(message)

    def play_round(self, player):
        hand = 0
        self.add_feedback(f"\n### {player.name}'s turn")
        while True:
            game_state = self.get_game_state(player.name, hand)
            decision = player.make_decision(game_state)

            if decision == 'stand':
                self.add_feedback(f"  - {player.name} stands with {hand}")
                break

            card = random.randint(1, 10)
            hand += card

            self.add_feedback(f"  - {player.name} hits and draws {card}, hand is now {hand}")

            if hand > 42:
                self.add_feedback(f"  - {player.name} busts with {hand}")
                break

        return min(hand, 42)

    def get_game_state(self, player_name, current_hand):
        return {
            "player_name": player_name,
            "current_hand": current_hand,
            "scores": self.scores
        }

    def play_game(self, custom_rewards=None):
        self.add_feedback("# Forty-Two Game")
        self.add_feedback("\n## Player order:")
        for i, player in enumerate(self.players, 1):
            self.add_feedback(f"{i}. {player.name}")

        self.add_feedback("\n## Game Play")
        for player in self.players:
            hand = self.play_round(player)
            if hand <= 42:
                self.scores[player.name] += hand

            self.add_feedback(f"  - {player.name} finished with {hand}")

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
        self.feedback = []
        for player in self.players:
            player.hand = 0

    @classmethod
    def run_single_game_with_feedback(cls, league, custom_rewards=None):
        game = cls(league, verbose=True, custom_rewards=custom_rewards)
        results = game.play_game(custom_rewards)
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