import itertools
import random

from games.base_game import BaseGame


class PrisonersDilemmaGame(BaseGame):
    starter_code = """
from games.prisoners_dilemma.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        my_opponent = game_state["opponent_name"]
        opponent_history = game_state["opponent_history"]
        my_history = game_state["my_history"]
        
        # Your code here
        decision = 'collude'  # or 'defect'
        
        # Add custom feedback (will appear in game output)
        self.add_feedback("Round number: " + str(game_state['round_number']))
        self.add_feedback("| Opponent history: " + str(opponent_history))
        
        return decision
"""

    game_instructions = """### Prisoner's Dilemma Game Instructions

Welcome to the Prisoner's Dilemma game! Your task is to implement the `make_decision` method in the `CustomPlayer` class.

#### 1. Game Objective
Maximize your score over multiple rounds by choosing to collude or defect against your opponents.

#### 2. Your Task
Implement the `make_decision` method to decide whether to 'collude' or 'defect' based on the game state.

#### 3. Available Information
The `game_state` parameter provides you with the following information:
- `round_number`: The current round number
- `player_name`: Your player's name
- `opponent_name`: Your current opponent's name
- `opponent_history`: A list of your opponent's past decisions against you
- `scores`: A dictionary of current scores for all players

#### 4. Scoring
The scoring is determined by a reward matrix. The default matrix is:
- Both collude: 4 points each
- Both defect: 0 points each
- One colludes, one defects: Defector gets 6 points, Colluder gets 0 points

#### 5. Strategy Tips
- Consider patterns in your opponent's history.
- Balance between cooperation and self-interest.
- Experiment with different strategies (e.g., tit-for-tat, always defect, etc.).
- Adapt your strategy based on the current scores and round number.

#### WARNING
When you log out, navigate away, or refresh the page, your code will be lost. Please save it!

Good luck and have fun!
"""

    def __init__(
        self,
        league,
        verbose=False,
        reward_matrix=None,
        rounds_per_pairing=5,
        collect_player_feedback=True,
    ):
        super().__init__(league, verbose)
        self.histories = {str(player.name): {} for player in self.players}
        self.reward_matrix = reward_matrix or {
            "collude,collude": (4, 4),
            "collude,defect": (0, 6),
            "defect,collude": (6, 0),
            "defect,defect": (0, 0),
        }
        self.rounds_per_pairing = rounds_per_pairing
        self.game_feedback = {"game": "prisoners_dilemma", "pairings": []}
        self.player_feedback = {}
        self.collect_player_feedback = collect_player_feedback
        self.scores = {str(player.name): 0 for player in self.players}

    def get_game_state(self, player_name, opponent_name, round_number):
        histories_copy = {}
        for p1, opponents in self.histories.items():
            histories_copy[str(p1)] = {}
            for p2, decisions in opponents.items():
                histories_copy[str(p1)][str(p2)] = list(decisions)

        state = {
            "round_number": round_number,
            "player_name": str(player_name),
            "opponent_name": str(opponent_name),
            "opponent_history": list(
                self.histories[str(opponent_name)].get(str(player_name), [])
            ),
            "my_history": list(
                self.histories[str(player_name)].get(str(opponent_name), [])
            ),
            "all_history": histories_copy,
            "scores": dict(self.scores),
        }
        return state

    def add_feedback(self, pairing_data):
        if self.verbose:
            self.game_feedback["pairings"].append(pairing_data)

    def add_player_feedback(self, player, round_number, opponent_name):
        if self.collect_player_feedback and player.feedback:
            player_name = str(player.name)
            if player_name not in self.player_feedback:
                self.player_feedback[player_name] = []

            feedback_entry = {
                "round": round_number,
                "opponent": str(opponent_name),
                "messages": list(player.feedback),
                "scores": {
                    "my_score": self.scores[player_name],
                    "opponent_score": self.scores[str(opponent_name)],
                },
            }
            self.player_feedback[player_name].append(feedback_entry)
            player.feedback = []

    def play_pairing(self, player1, player2):
        pairing_data = {
            "player1": str(player1.name),
            "player2": str(player2.name),
            "rounds": [],
        }

        for round_number in range(1, self.rounds_per_pairing + 1):
            game_state1 = self.get_game_state(player1.name, player2.name, round_number)
            game_state2 = self.get_game_state(player2.name, player1.name, round_number)

            random.seed()

            try:
                decision1 = player1.make_decision(game_state1)
                if decision1 not in ["defect", "collude"]:
                    decision1 = "collude"
            except Exception as e:
                decision1 = "collude"

            try:
                decision2 = player2.make_decision(game_state2)
                if decision2 not in ["defect", "collude"]:
                    decision2 = "collude"
            except Exception as e:
                decision2 = "collude"

            # Update histories
            p1_name = str(player1.name)
            p2_name = str(player2.name)

            if p1_name not in self.histories:
                self.histories[p1_name] = {}
            if p2_name not in self.histories[p1_name]:
                self.histories[p1_name][p2_name] = []
            self.histories[p1_name][p2_name].append(decision1)

            if p2_name not in self.histories:
                self.histories[p2_name] = {}
            if p1_name not in self.histories[p2_name]:
                self.histories[p2_name][p1_name] = []
            self.histories[p2_name][p1_name].append(decision2)

            # Calculate scores using string key
            key = f"{decision1},{decision2}"
            score1, score2 = self.reward_matrix[key]
            self.scores[p1_name] += score1
            self.scores[p2_name] += score2

            round_data = {
                "round_number": round_number,
                "actions": {p1_name: decision1, p2_name: decision2},
                "scores": {
                    p1_name: self.scores[p1_name],
                    p2_name: self.scores[p2_name],
                },
            }
            pairing_data["rounds"].append(round_data)

            self.add_player_feedback(player1, round_number, player2.name)
            self.add_player_feedback(player2, round_number, player1.name)

        self.add_feedback(pairing_data)

    def play_game(self, custom_rewards=None):
        if custom_rewards:
            self.reward_matrix = {
                "collude,collude": (custom_rewards[0], custom_rewards[0]),
                "collude,defect": (custom_rewards[1], custom_rewards[2]),
                "defect,collude": (custom_rewards[2], custom_rewards[1]),
                "defect,defect": (custom_rewards[3], custom_rewards[3]),
            }

        self.game_feedback["game_info"] = {
            "players": [str(player.name) for player in self.players],
            "reward_matrix": self.reward_matrix,
            "rounds_per_pairing": self.rounds_per_pairing,
        }

        player_pairs = list(itertools.combinations(self.players, 2))
        random.shuffle(player_pairs)

        for player1, player2 in player_pairs:
            self.play_pairing(player1, player2)

        self.game_feedback["final_scores"] = dict(self.scores)

        return {"points": dict(self.scores), "score_aggregate": dict(self.scores)}

    def reset(self):
        super().reset()
        self.histories = {str(player.name): {} for player in self.players}
        self.game_feedback = {"pairings": []}
        self.player_feedback = {}
        self.scores = {str(player.name): 0 for player in self.players}

    @classmethod
    def run_single_game_with_feedback(cls, league, custom_rewards=None):
        game = cls(league, verbose=True, collect_player_feedback=True)
        results = game.play_game(custom_rewards)
        return {
            "results": results,
            "feedback": game.game_feedback,
            "player_feedback": game.player_feedback,
        }

    @classmethod
    def run_simulations(cls, num_simulations, league, custom_rewards=None):
        game = cls(league, collect_player_feedback=False)
        total_points = {str(player.name): 0 for player in game.players}
        defections = {str(player.name): 0 for player in game.players}
        collusions = {str(player.name): 0 for player in game.players}

        for _ in range(num_simulations):
            game.reset()
            results = game.play_game(custom_rewards)

            for player, points in results["points"].items():
                total_points[str(player)] += points

            for player_name, opponents in game.histories.items():
                for opponent_name, decisions in opponents.items():
                    defections[str(player_name)] += decisions.count("defect")
                    collusions[str(player_name)] += decisions.count("collude")

        return {
            "total_points": total_points,
            "num_simulations": num_simulations,
            "table": {"defections": defections, "collusions": collusions},
        }
