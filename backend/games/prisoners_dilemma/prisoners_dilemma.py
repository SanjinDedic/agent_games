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

    def __init__(self, league, verbose=False, reward_matrix=None, rounds_per_pairing=5):
        super().__init__(league, verbose)
        self.histories = {player.name: {} for player in self.players}
        self.reward_matrix = reward_matrix or {
            ('collude', 'collude'): (1, 1),
            ('collude', 'defect'): (0, 2),
            ('defect', 'collude'): (2, 0),
            ('defect', 'defect'): (0, 0)
        }
        self.rounds_per_pairing = rounds_per_pairing
        self.feedback = []

    def add_feedback(self, message):
        if self.verbose:
            self.feedback.append(message)

    def color_decision(self, decision):
        if decision == 'collude':
            return '<span style="color: green;">collude</span>'
        elif decision == 'defect':
            return '<span style="color: red;">defect</span>'
        return decision

    def play_pairing(self, player1, player2):
        self.add_feedback(f"\n## Pairing: {player1.name} vs {player2.name}")
        for round_number in range(1, self.rounds_per_pairing + 1):
            game_state1 = self.get_game_state(player1.name, player2.name, round_number)
            game_state2 = self.get_game_state(player2.name, player1.name, round_number)

            decision1 = player1.make_decision(game_state1)
            decision2 = player2.make_decision(game_state2)

            self.histories[player1.name].setdefault(player2.name, []).append(decision1)
            self.histories[player2.name].setdefault(player1.name, []).append(decision2)

            self.update_scores(player1, decision1, player2, decision2)

            colored_decision1 = self.color_decision(decision1)
            colored_decision2 = self.color_decision(decision2)

            self.add_feedback(f"\n**Round {round_number}** {player1.name}: {colored_decision1}, {player2.name}: {colored_decision2}  \n")
            self.add_feedback(f"- {player1.name} score: {self.scores[player1.name]}, {player2.name} score: {self.scores[player2.name]}")

    def update_scores(self, player1, decision1, player2, decision2):
        score1, score2 = self.reward_matrix[(decision1, decision2)]
        self.scores[player1.name] += score1
        self.scores[player2.name] += score2

    def get_game_state(self, player_name, opponent_name, round_number):
        return {
            "round_number": round_number,
            "player_name": player_name,
            "opponent_name": opponent_name,
            "opponent_history": self.histories[opponent_name].get(player_name, []),
            "my_history": self.histories[player_name].get(opponent_name, []),
            "all_history": self.histories,
            "scores": self.scores
        }

    def play_game(self, custom_rewards=None):
        self.add_feedback("# Prisoner's Dilemma Game")
        self.add_feedback("\n## Players:")
        for player in self.players:
            self.add_feedback(f"  - {player.name}")

        player_pairs = list(itertools.combinations(self.players, 2))
        random.shuffle(player_pairs)

        for player1, player2 in player_pairs:
            self.play_pairing(player1, player2)

        self.add_feedback("\n## Final Scores:")
        for player, score in self.scores.items():
            self.add_feedback(f"  - {player}: {score}")

        return {"points": self.scores, "score_aggregate": self.scores}

    def reset(self):
        super().reset()
        self.histories = {player.name: {} for player in self.players}
        self.feedback = []

    @classmethod
    def run_single_game_with_feedback(cls, league, custom_rewards=None):
        game = cls(league, verbose=True)
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
            #print("HERE ARE THE RESULTS", results)
            winner = max(results["points"], key=results["points"].get)
            total_wins[winner] += 1

        return {
            "total_points": total_points,
            "total_wins": total_wins,
            "num_simulations": num_simulations
        }
    