from games.base_game import BaseGame
import random
import itertools

class PrisonersDilemmaGame(BaseGame):
    starter_code = '''
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        my_opponent = game_state["opponent_name"]
        opponent_history = game_state["opponent_history"]
        my_history = game_state["my_history"]
        
        # Your code here
        decision = 'collude'  # or 'defect'
        
        # Add custom feedback (will appear in blue in the game output)
        self.add_feedback(f"Round {game_state['round_number']}: Opponent history: {opponent_history}, My history: {my_history}, My decision: {decision}")
        
        return decision
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

    def __init__(self, league, verbose=False, reward_matrix=None, rounds_per_pairing=5, collect_player_feedback=True):
            super().__init__(league, verbose)
            self.histories = {player.name: {} for player in self.players}
            self.reward_matrix = reward_matrix or {
                ('collude', 'collude'): (4, 4),
                ('collude', 'defect'): (0, 6),
                ('defect', 'collude'): (6, 0),
                ('defect', 'defect'): (0, 0)
            }
            self.rounds_per_pairing = rounds_per_pairing
            self.game_feedback = []
            self.player_feedback = []
            self.collect_player_feedback = collect_player_feedback

    def add_feedback(self, message):
        if self.verbose:
            self.game_feedback.append(message)
            self.player_feedback.append(message)

    def color_decision(self, decision):
        if decision == 'collude':
            return '<span style="color: green;"><b>collude</b></span>'
        elif decision == 'defect':
            return '<span style="color: red;"><b>defect</b></span>'
        return decision

    def play_pairing(self, player1, player2):
        self.add_feedback(f"\n## Pairing: &#128100;{player1.name} vs &#128100;{player2.name}")
        for round_number in range(1, self.rounds_per_pairing + 1):
            game_state1 = self.get_game_state(player1.name, player2.name, round_number)
            game_state2 = self.get_game_state(player2.name, player1.name, round_number)
            try:
                decision1 = player1.make_decision(game_state1)
            except:
                decision1 = 'collude'
                self.add_feedback(player1.name + " invalid code, decision defaulting to collude")
            try:
                decision2 = player2.make_decision(game_state2)
            except:
                decision2 = 'collude'
                self.add_feedback(player2.name + " invalid code, decision defaulting to collude")
            self.histories[player1.name].setdefault(player2.name, []).append(decision1)
            self.histories[player2.name].setdefault(player1.name, []).append(decision2)

            self.update_scores(player1, decision1, player2, decision2)

            self.add_feedback(f"<table>")
            self.add_feedback(f"<tr style=\"border:0px\"><th style=\"border: 0px\"><u>Round {round_number}</u></th><th>&#128100;{player1.name}</th><th>&#128100;{player2.name}</th></tr>")
            self.add_feedback(f"<tr style=\"border:0px\"><td style=\"border:0px;white-space:nowrap;\"><b>action</b></td><td>{self.color_decision(decision1)}</td><td>{self.color_decision(decision2)}</td></tr>")
            self.add_feedback(f"<tr style=\"border:0px\"><td style=\"border:0px;white-space:nowrap;\"><b>score</b></td><td>{self.scores[player1.name]}</td><td>{self.scores[player2.name]}</td></tr>")
            self.add_feedback(f"</table>")
            
            # Add player feedback
            self.add_player_feedback(player1)
            self.add_player_feedback(player2)

    def add_player_feedback(self, player):
        if self.collect_player_feedback and player.feedback:
            feedback = f"\n<b>{player.name}'s feedback: </b>"
            self.player_feedback.append(feedback)
            for message in player.feedback:
                colored_message = f"<span style='color: blue;'>{message}</span>"
                self.player_feedback.append(colored_message)
            player.feedback = []  # Clear the feedback after adding it

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
        if custom_rewards:
            self.reward_matrix = {
                ('collude', 'collude'): (custom_rewards[0], custom_rewards[0]),
                ('collude', 'defect'): (custom_rewards[1], custom_rewards[2]),
                ('defect', 'collude'): (custom_rewards[2], custom_rewards[1]),
                ('defect', 'defect'): (custom_rewards[3], custom_rewards[3])
            }

        self.add_feedback("# Prisoner's Dilemma Game")
        self.add_feedback("\n### Players:")
        for player in self.players:
            self.add_feedback(f"  - &#128100;{player.name}")

        player_pairs = list(itertools.combinations(self.players, 2))
        random.shuffle(player_pairs)

        for player1, player2 in player_pairs:
            self.play_pairing(player1, player2)

        self.add_feedback("\n## Final Scores:")
        for player, score in self.scores.items():
            self.add_feedback(f"  - &#128100;{player}: <b>{score}</b>")

        return {"points": self.scores, "score_aggregate": self.scores}

    def reset(self):
        super().reset()
        self.histories = {player.name: {} for player in self.players}
        self.game_feedback = []
        self.player_feedback = []

    @classmethod
    def run_single_game_with_feedback(cls, league, custom_rewards=None):
        game = cls(league, verbose=True, collect_player_feedback=True)
        results = game.play_game(custom_rewards)
        game_feedback = "\n".join(game.game_feedback)
        player_feedback = "\n".join(game.player_feedback)
        return {
            "results": results,
            "feedback": game_feedback,
            "player_feedback": player_feedback
        }

    @classmethod
    def run_simulations(cls, num_simulations, league, custom_rewards=None):
        game = cls(league, collect_player_feedback=False)
        total_points = {player.name: 0 for player in game.players}
        defections = {player.name: 0 for player in game.players}
        collusions = {player.name: 0 for player in game.players}

        for _ in range(num_simulations):
            game.reset()
            results = game.play_game(custom_rewards)
            
            for player, points in results["points"].items():
                total_points[player] += points

            for player_name, opponents in game.histories.items():
                for opponent_name, decisions in opponents.items():
                    defections[player_name] += decisions.count('defect')
                    collusions[player_name] += decisions.count('collude')

        return {
            "total_points": total_points,
            "num_simulations": num_simulations,
            "table": {
                "defections": defections,
                "collusions": collusions
            }
        }