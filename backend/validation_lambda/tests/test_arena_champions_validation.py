"""Arena Champions game-rule validation, exercised through run_validation.

The game validates stat proportions in play_game (each within [0.2, 0.4] and
summing to 1.0); a violation aborts the run, so the envelope comes back as a
validation failure. These used to run through the deleted server submission
route — the invariant under test is the executor + game engine behavior, so
they live with the executor now.
"""

from backend.validation_lambda.executor import run_validation


def _validate(code: str) -> dict:
    return run_validation(
        code=code, game_name="arena_champions", team_name="arena_team"
    )


VALID_AGENT = """
from games.arena_champions.player import Player
class CustomPlayer(Player):
    def __init__(self):
        super().__init__()
        # proportions within [0.2, 0.4] and sum to 1.0
        self.attack_proportion = 0.30
        self.defense_proportion = 0.20
        self.max_health_proportion = 0.25
        self.dexterity_proportion = 0.25
        self.set_to_original_stats()

    def make_combat_decision(self, opponent_stats, turn, your_role, last_opponent_action=None):
        return "attack" if your_role == "attacker" else "defend"
"""


def test_valid_agent_passes():
    result = _validate(VALID_AGENT)
    assert result["status"] == "success", result["message"]
    assert result["simulation_results"] is not None


def test_fails_when_sum_of_proportions_exceeds_one():
    # Each within [0.2, 0.4], but sum = 1.2
    bad_sum_code = """
from games.arena_champions.player import Player
class CustomPlayer(Player):
    def __init__(self):
        super().__init__()
        self.attack_proportion = 0.40
        self.defense_proportion = 0.40
        self.max_health_proportion = 0.20
        self.dexterity_proportion = 0.20
        self.set_to_original_stats()

    def make_combat_decision(self, opponent_stats, turn, your_role, last_opponent_action=None):
        return "attack" if your_role == "attacker" else "defend"
"""
    result = _validate(bad_sum_code)
    assert result["status"] == "error", result
    assert result["message"]


def test_fails_when_max_health_out_of_range():
    bad_max_code = """
from games.arena_champions.player import Player
class CustomPlayer(Player):
    def __init__(self):
        super().__init__()
        self.attack_proportion = 0.30
        self.defense_proportion = 0.20
        self.max_health_proportion = 11111  # invalid
        self.dexterity_proportion = 0.25
        self.set_to_original_stats()

    def make_combat_decision(self, opponent_stats, turn, your_role, last_opponent_action=None):
        return "attack" if your_role == "attacker" else "defend"
"""
    result = _validate(bad_max_code)
    assert result["status"] == "error", result
    assert result["message"]
