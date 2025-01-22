import random

from backend.games.prisoners_dilemma.player import Player


class AlwaysCooperate(Player):
    """Player that always cooperates"""

    def make_decision(self, game_state):
        return "collude"


class AlwaysDefect(Player):
    """Player that always defects"""

    def make_decision(self, game_state):
        return "defect"


class TitForTat(Player):
    """Player that starts with cooperation and then copies opponent's last move"""

    def make_decision(self, game_state):
        opponent_history = game_state["opponent_history"]
        if not opponent_history:
            return "collude"
        return opponent_history[-1]


class GradualPlayer(Player):
    """Player that becomes more vengeful as opponent defects more"""

    def make_decision(self, game_state):
        opponent_history = game_state["opponent_history"]
        if not opponent_history:
            return "collude"

        defection_count = opponent_history.count("defect")
        if defection_count == 0:
            return "collude"

        # Consider recent history more heavily
        recent_moves = opponent_history[-3:]
        if "defect" in recent_moves:
            return "defect"

        return "collude"


class RandomPlayer(Player):
    """Player that makes random decisions"""

    def make_decision(self, game_state):
        return random.choice(["collude", "defect"])


players = [
    AlwaysCooperate(),
    AlwaysDefect(),
    TitForTat(),
    GradualPlayer(),
    RandomPlayer(),
]
