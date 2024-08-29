from games.base_game import BaseGame
import random
import itertools

class PrisonersDilemmaGame(BaseGame):
    starter_code = '''
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        # Your code here
        return 'collude'  # or 'defect'
'''

    game_instructions = '''
<h1>Prisoner's Dilemma Game Instructions</h1>

<p>Welcome to the Prisoner's Dilemma game! Your task is to implement the <code>make_decision</code> method in the <code>CustomPlayer</code> class.</p>

<h2>1. Game Objective</h2>
<p>Maximize your score over multiple rounds by choosing to collude or defect against your opponents.</p>

<h2>2. Your Task</h2>
<p>Implement the <code>make_decision</code> method to decide whether to 'collude' or 'defect' based on the game state.</p>

<h2>3. Available Information</h2>
<p>The <code>game_state</code> parameter provides you with the following information:</p>
<ul>
    <li><code>round_number</code>: The current round number</li>
    <li><code>player_name</code>: Your player's name</li>
    <li><code>opponent_name</code>: Your current opponent's name</li>
    <li><code>opponent_history</code>: A list of your opponent's past decisions against you</li>
    <li><code>scores</code>: A dictionary of current scores for all players</li>
</ul>

<h2>4. Scoring</h2>
<p>The scoring is determined by a reward matrix. The default matrix is:</p>
<ul>
    <li>Both collude: 3 points each</li>
    <li>Both defect: 1 point each</li>
    <li>One colludes, one defects: Defector gets 5 points, Colluder gets 0 points</li>
</ul>

<h2>5. Implementation Example</h2>
<pre><code>
def make_decision(self, game_state):
    opponent_history = game_state['opponent_history']
    if not opponent_history:
        return 'collude'
    if opponent_history[-1] == 'defect':
        return 'defect'
    return 'collude'
</code></pre>

<h2>6. Strategy Tips</h2>
<ul>
    <li>Consider patterns in your opponent's history</li>
    <li>Balance between cooperation and self-interest</li>
    <li>Experiment with different strategies (e.g., tit-for-tat, always defect, etc.)</li>
    <li>Adapt your strategy based on the current scores and round number</li>
</ul>

<p>Good luck and have fun!</p>
'''

    def __init__(self, league, verbose=False, reward_matrix=None):
        super().__init__(league, verbose)
        self.histories = {player.name: {} for player in self.players}
        self.reward_matrix = reward_matrix or {
            ('collude', 'collude'): (3, 3),
            ('collude', 'defect'): (0, 5),
            ('defect', 'collude'): (5, 0),
            ('defect', 'defect'): (1, 1)
        }
        self.round_number = 0
        self.feedback = []

    def add_feedback(self, message):
        if self.verbose:
            self.feedback.append(message)

    def play_round(self):
        self.round_number += 1
        self.add_feedback(f"\n## Round {self.round_number}")

        # Create all possible pairs of players
        player_pairs = list(itertools.combinations(self.players, 2))

        # Shuffle the pairs to randomize the order of play
        random.shuffle(player_pairs)

        for player1, player2 in player_pairs:
            game_state1 = self.get_game_state(player1.name, player2.name)
            game_state2 = self.get_game_state(player2.name, player1.name)

            decision1 = player1.make_decision(game_state1)
            decision2 = player2.make_decision(game_state2)

            self.histories[player1.name].setdefault(player2.name, []).append(decision1)
            self.histories[player2.name].setdefault(player1.name, []).append(decision2)

            self.update_scores(player1, decision1, player2, decision2)

            self.add_feedback(f"  - {player1.name} vs {player2.name}: {decision1} vs {decision2}")
            self.add_feedback(f"    * {player1.name} score: {self.scores[player1.name]}, {player2.name} score: {self.scores[player2.name]}")

    def update_scores(self, player1, decision1, player2, decision2):
        score1, score2 = self.reward_matrix[(decision1, decision2)]
        self.scores[player1.name] += score1
        self.scores[player2.name] += score2

    def get_game_state(self, player_name, opponent_name):
        return {
            "round_number": self.round_number,
            "player_name": player_name,
            "opponent_name": opponent_name,
            "opponent_history": self.histories[opponent_name].get(player_name, []),
            "scores": self.scores
        }

    def play_game(self, num_rounds=5):
        self.add_feedback("# Prisoner's Dilemma Game")
        self.add_feedback("\n## Players:")
        for player in self.players:
            self.add_feedback(f"  - {player.name}")

        for _ in range(num_rounds):
            self.play_round()

        self.add_feedback("\n## Final Scores:")
        for player, score in self.scores.items():
            self.add_feedback(f"  - {player}: {score}")

        return self.assign_points(self.scores)

    def assign_points(self, scores, custom_rewards=None):
        rewards = custom_rewards or [10, 8, 6, 4, 3, 2, 1]
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

        self.add_feedback("\n## Points Awarded:")
        for player, point in points.items():
            self.add_feedback(f"  - {player}: {point}")

        return {"points": points, "score_aggregate": scores}

    def reset(self):
        super().reset()
        self.histories = {player.name: {} for player in self.players}
        self.round_number = 0
        self.feedback = []

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
        # Create a game instance to get the players
        game = cls(league)
        
        total_points = {player.name: 0 for player in game.players}
        total_wins = {player.name: 0 for player in game.players}

        for _ in range(num_simulations):
            game.reset()
            results = game.play_game()
            
            for player, points in results["points"].items():
                total_points[player] += points
            
            winner = max(results["points"], key=results["points"].get)
            total_wins[winner] += 1

        return {
            "total_points": total_points,
            "total_wins": total_wins,
            "num_simulations": num_simulations
        }