import random

from backend.config import ROOT_DIR
from backend.games.base_game import BaseGame
from backend.games.greedy_pig.player import Player as GreedyPigPlayer


class GreedyPigGame(BaseGame):
    starter_code = """
from games.greedy_pig.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        my_unbanked = game_state["unbanked_money"][self.name]
        my_banked = game_state["banked_money"][self.name]
        my_current_rank = self.my_rank(game_state) # based on total money (banked + unbanked)
        
        decision = random.choice(['continue', 'bank'])
        
        # Add custom feedback (will appear in blue in the game output)
        self.add_feedback(f"game state: {game_state}, my decision: {decision}")
        
        return decision
"""

    game_instructions = """
<h1>Greedy Pig Game Instructions</h1>

<p>Welcome to the Greedy Pig game! Your task is to implement the <code>make_decision</code> method in the <code>CustomPlayer</code> class.</p>

<h2>1. Game Objective</h2>
<p>Be the first player to bank 100 points.</p>

<h2>2. Your Task</h2>
<p>Implement the <code>make_decision</code> method to decide whether to 'continue' rolling or 'bank' your current unbanked money.</p>

<h2>3. Available Information</h2>
<p>The <code>game_state</code> parameter provides you with the following information:</p>
<ul>
    <li><code>round_no</code>: The current round number</li>
    <li><code>roll_no</code>: The number of rolls in the current turn</li>
    <li><code>players_banked_this_round</code>: List of players who have banked in this round</li>
    <li><code>banked_money</code>: Dictionary of each player's banked money</li>
    <li><code>unbanked_money</code>: Dictionary of each player's unbanked money</li>
</ul>

<h2>4. Helpful Methods</h2>
<p>You can use the following methods in your implementation:</p>
<ul>
    <li><code>self.my_rank(game_state)</code>: Returns your current rank based on total money (banked + unbanked)</li>
    <li><code>self.add_feedback(message)</code>: Adds a custom feedback message that will be displayed in the game output</li>
</ul>

<h2>5. Implementation Example</h2>
<pre><code>
def make_decision(self, game_state):
    my_unbanked = game_state["unbanked_money"][self.name]
    my_banked = game_state["banked_money"][self.name]
    my_current_rank = self.my_rank(game_state)

    if my_unbanked > 20 or (my_banked + my_unbanked >= 100):
        decision = 'bank'
    elif my_current_rank > 2 and game_state["roll_no"] > 3:
        decision = 'bank'
    else:
        decision = 'continue'

    self.add_feedback(f"game state: {game_state}, my decision: {decision}")
    return decision
</code></pre>

<h2>6. Strategy Tips</h2>
<ul>
    <li>Consider your current rank when making decisions</li>
    <li>Be aware of how close you are to winning (100 points)</li>
    <li>Balance the risk of rolling again with the potential reward</li>
    <li>Observe other players' strategies through the <code>players_banked_this_round</code> list</li>
    <li>Use the <code>add_feedback</code> method to log your decision-making process and debug your strategy</li>
</ul>

<p>Good luck and have fun!</p>
"""

    def __init__(self, league, verbose=False, custom_rewards=None):
        super().__init__(league, verbose)
        self.active_players = list(self.players)
        self.players_banked_this_round = []
        self.round_no = 0
        self.roll_no = 0
        self.game_over = False
        self.custom_rewards = custom_rewards or [10, 8, 6, 4, 3, 2, 1]
        # Initialize feedback as string for markdown
        self.game_feedback = ""
        self.player_feedback = []

    def add_feedback(self, message):
        """Add a feedback message if verbose mode is on"""
        if self.verbose:
            if isinstance(message, str):
                self.game_feedback += message + "\n"
            else:
                self.game_feedback += str(message) + "\n"
                self.game_feedback.append(message)

    def add_player_feedback(self, player):
        if player.feedback:
            feedback = f"\n<b>{player.name}'s feedback:</b>"
            self.player_feedback.append(feedback)
            for message in player.feedback:
                colored_message = f"<span style='color: blue;'>{message}</span>"
                self.player_feedback.append(colored_message)
            player.feedback = []  # Clear the feedback after adding it

    def roll_dice(self):
        return random.randint(1, 6)

    def get_game_state(self):
        return {
            "round_no": self.round_no,
            "roll_no": self.roll_no,
            "players_banked_this_round": self.players_banked_this_round,
            "banked_money": {
                player.name: player.banked_money for player in self.players
            },
            "unbanked_money": {
                player.name: player.unbanked_money for player in self.players
            },
        }

    def play_round(self):
        self.players_banked_this_round = []
        self.round_no += 1
        self.roll_no = 0

        self.add_feedback(f"\n## Round {self.round_no}")

        while True:
            self.roll_no += 1
            random.seed()  # Reset random seed each roll to prevent manipulation
            roll = self.roll_dice()
            self.add_feedback(f"\n### Roll {self.roll_no}")
            self.add_feedback(f"\n<table>")
            feedback_row = ""
            feedback_row += f'<tr style="border:0px"><th style="border: 0px"></th>'
            for player in self.active_players:
                feedback_row += f"<th>&#128100;{player.name}</th>"
            feedback_row += f"</tr>"
            self.add_feedback(feedback_row)

            feedback_row = f'<tr style="border: 0px">'
            if roll == 1:
                feedback_row += f'<td style="border:0px;white-space:nowrap;">&#127922; = <span style="color:red"><b>{roll}</b></span></td>'
                for player in self.active_players:
                    if player.unbanked_money > 0:
                        feedback_row += f'<td style="color:red">$0</td>'
                    else:
                        feedback_row += f"<td>$0</td>"
                    player.reset_unbanked_money()
                feedback_row += f"</tr>"
                self.add_feedback(feedback_row)
                self.add_feedback(f"</table>")
                break

            feedback_row += f'<td style="border:0px;white-space:nowrap;">&#127922; = <b>{roll}</b></td>'
            for player in self.active_players.copy():
                feedback_row += f"<td>${player.unbanked_money + roll}</td>"
            feedback_row += f"</tr>"
            self.add_feedback(feedback_row)

            feedback_row = (
                f'<tr style="border:0px"><td style="border: 0px"><b>Action</b></td>'
            )
            for player in self.active_players.copy():
                if not player.has_banked_this_turn:
                    player.unbanked_money += roll
                    try:
                        # Create a fresh game state for each player
                        player_state = self.get_game_state()
                        decision = player.make_decision(player_state)
                    except Exception as e:
                        print(f"Error in player {player.name}'s decision: {e}")
                        decision = "bank"

                    if decision == "bank":
                        feedback_row += f"<td>&#128181; bank</td>"
                        player.bank_money()
                        player.has_banked_this_turn = True
                        self.players_banked_this_round.append(player.name)
                        self.active_players.remove(player)
                    else:
                        feedback_row += f"<td></td>"

                    self.add_player_feedback(player)

            feedback_row += f"</tr>"
            self.add_feedback(feedback_row)
            self.add_feedback(f"</table>")

            for player in self.active_players:
                if player.banked_money + player.unbanked_money >= 100:
                    self.game_over = True
                    return

            if len(self.active_players) == 0:
                break

        for player in self.players:
            player.reset_turn()

    def play_game(self, custom_rewards=None):
        self.add_feedback("# Greedy Pig Game")
        random.shuffle(self.players)

        while not self.game_over:
            self.active_players = list(self.players)
            self.play_round()
            self.add_feedback("\n### End of Round")
            for player in self.players:
                self.add_feedback(
                    f"  - &#128100;<b>{player.name}</b>: ${player.banked_money}"
                )

        game_state = self.get_game_state()
        results = self.assign_points(game_state, custom_rewards)

        self.add_feedback("\n## Final Results")
        for player, points in results["points"].items():
            self.add_feedback(f"- {player}: {points} points")

        return results

    def assign_points(self, game_state, custom_rewards=None):
        rewards = custom_rewards or self.custom_rewards
        score_aggregate = {
            player: game_state["banked_money"][player]
            + game_state["unbanked_money"][player]
            for player in game_state["banked_money"]
        }
        sorted_players = sorted(
            score_aggregate.items(), key=lambda x: x[1], reverse=True
        )

        points = {}
        last_score = None
        last_reward = 0
        reward_index = 0

        for i, (player, score) in enumerate(sorted_players):
            if score != last_score:
                if reward_index < len(rewards):
                    last_reward = rewards[reward_index]
                    reward_index += 1
                else:
                    last_reward = 0

            points[player] = last_reward
            last_score = score

        return {"points": points, "score_aggregate": score_aggregate}

    def reset(self):
        """Reset game state"""
        super().reset()  # Calls BaseGame.reset()
        self.histories = {str(player.name): {} for player in self.players}
        self.game_feedback = ""  # Reset to empty string
        self.player_feedback = []
        self.scores = {str(player.name): 0 for player in self.players}
        # Reset GreedyPigGame specific state
        self.round_no = 0
        self.roll_no = 0
        self.game_over = False
        self.active_players = list(self.players)  # Reset active players list

        # Reset all player states
        for player in self.players:
            player.banked_money = 0
            player.unbanked_money = 0
            player.has_banked_this_turn = False

    def run_single_game_with_feedback(self, custom_rewards=None):
        """Run a single game with feedback"""
        # Enable feedback for this run
        self.verbose = True
        self.collect_player_feedback = True

        # Run the game
        results = self.play_game(custom_rewards)

        return {
            "results": results,
            "feedback": self.game_feedback,  # Already a string
            "player_feedback": self.player_feedback,
        }

    def run_simulations(self, num_simulations, league, custom_rewards=None):
        """Run multiple simulations - now an instance method"""
        total_points = {str(player.name): 0 for player in self.players}
        rolls = {str(player.name): 0 for player in self.players}
        holds = {str(player.name): 0 for player in self.players}

        for _ in range(num_simulations):
            self.reset()  # Reset game state but keep players
            results = self.play_game(custom_rewards)

            # Update totals
            for player, points in results["points"].items():
                total_points[str(player)] += points

            # Update statistics if available
            if "table" in results:
                for player_name, stats in results["table"].get("rolls", {}).items():
                    rolls[str(player_name)] += stats
                for player_name, stats in results["table"].get("holds", {}).items():
                    holds[str(player_name)] += stats

        return {
            "total_points": total_points,
            "num_simulations": num_simulations,
            "table": {"rolls": rolls, "holds": holds},
        }
