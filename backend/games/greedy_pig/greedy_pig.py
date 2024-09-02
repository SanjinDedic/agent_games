from games.base_game import BaseGame
import random
import os
import time

class GreedyPigGame(BaseGame):
    starter_code = '''
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        # Your code here
        return 'continue'  # or 'bank'
'''

    game_instructions = '''
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
</ul>

<h2>5. Implementation Example</h2>
<pre><code>
def make_decision(self, game_state):
    my_unbanked = game_state["unbanked_money"][self.name]
    my_banked = game_state["banked_money"][self.name]
    my_current_rank = self.my_rank(game_state)

    if my_unbanked > 20 or (my_banked + my_unbanked >= 100):
        return 'bank'
    elif my_current_rank > 2 and game_state["roll_no"] > 3:
        return 'bank'
    else:
        return 'continue'
</code></pre>

<h2>6. Strategy Tips</h2>
<ul>
    <li>Consider your current rank when making decisions</li>
    <li>Be aware of how close you are to winning (100 points)</li>
    <li>Balance the risk of rolling again with the potential reward</li>
    <li>Observe other players' strategies through the <code>players_banked_this_round</code> list</li>
</ul>

<p>Good luck and have fun!</p>
'''

    def __init__(self, league, verbose=False, custom_rewards=None):
        super().__init__(league, verbose)
        self.active_players = list(self.players)
        self.players_banked_this_round = []
        self.round_no = 0
        self.roll_no = 0
        self.game_over = False
        self.custom_rewards = custom_rewards or [10, 8, 6, 4, 3, 2, 1]
        self.feedback = []

    def add_feedback(self, message):
        if self.verbose:
            self.feedback.append(message)

    def roll_dice(self):
        return random.randint(1, 6)

    def get_game_state(self):
        return {
            "round_no": self.round_no,
            "roll_no": self.roll_no,
            "players_banked_this_round": self.players_banked_this_round,
            "banked_money": {player.name: player.banked_money for player in self.players},
            "unbanked_money": {player.name: player.unbanked_money for player in self.players},
        }

    def play_round(self):
        self.players_banked_this_round = []
        self.round_no += 1
        self.roll_no = 0

        self.add_feedback(f"\n## Round {self.round_no}")

        while True:
            self.roll_no += 1
            roll = self.roll_dice()
            self.add_feedback(f"\n### Roll {self.roll_no}: Dice shows {roll}")

            if roll == 1:
                self.add_feedback("  - Oops! Rolled a 1. All players lose their unbanked money.")
                for player in self.active_players:
                    if player.unbanked_money > 0:
                        self.add_feedback(f"    * {player.name} loses ${player.unbanked_money} of unbanked money.")
                    player.reset_unbanked_money()
                break

            for player in self.active_players.copy():
                if not player.has_banked_this_turn:
                    player.unbanked_money += roll
                    self.add_feedback(f"  - {player.name} now has ${player.unbanked_money} unbanked.")
                    decision = player.make_decision(self.get_game_state())
                    if decision == 'bank':
                        self.add_feedback(f"    * {player.name} decides to bank ${player.unbanked_money}.")
                        player.bank_money()
                        player.has_banked_this_turn = True
                        self.players_banked_this_round.append(player.name)
                        self.active_players.remove(player)

            for player in self.active_players:
                if player.banked_money + player.unbanked_money >= 100:
                    self.game_over = True
                    return

        for player in self.players:
            player.reset_turn()

    def play_game(self, custom_rewards=None):
        self.add_feedback("# Greedy Pig Game")
        random.shuffle(self.players)
        self.add_feedback("\n## Initial player order:")
        for i, player in enumerate(self.players, 1):
            self.add_feedback(f"{i}. {player.name}")

        while not self.game_over:
            self.active_players = list(self.players)
            self.play_round()
            self.add_feedback("\n### End of Round Summary")
            for player in self.players:
                self.add_feedback(f"  - {player.name}: ${player.banked_money}")

        game_state = self.get_game_state()
        results = self.assign_points(game_state, custom_rewards)
        
        self.add_feedback("\n## Final Results")
        for player, points in results["points"].items():
            self.add_feedback(f"- {player}: {points} points")
        
        return results

    def assign_points(self, game_state, custom_rewards=None):
        rewards = custom_rewards or self.custom_rewards
        score_aggregate = {player: game_state['banked_money'][player] + game_state['unbanked_money'][player] for player in game_state['banked_money']}
        sorted_players = sorted(score_aggregate.items(), key=lambda x: x[1], reverse=True)

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
        super().reset()
        self.active_players = list(self.players)
        self.players_banked_this_round = []
        self.round_no = 0
        self.roll_no = 0
        self.game_over = False
        self.feedback = []

        for player in self.players:
            player.banked_money = 0
            player.unbanked_money = 0
            player.has_banked_this_turn = False

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
            "num_simulations": num_simulations,
            "table":{
                "total_wins": total_wins,
                "lala2": 2,
                "lala3": 3,
            }
        }