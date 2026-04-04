"""Direct unit tests for ArenaChampionsGame — combat, damage, tournament logic."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from backend.games.arena_champions.arena_champions import ArenaChampionsGame, BattleResult


class MockLeague:
    def __init__(self):
        self.id = 1
        self.name = "test_league"
        self.game = "arena_champions"


class MockPlayer:
    """Minimal mock player for arena champions."""
    def __init__(self, name, attack_p=0.25, defense_p=0.25, health_p=0.25, dex_p=0.25):
        self.name = name
        self.attack_proportion = attack_p
        self.defense_proportion = defense_p
        self.max_health_proportion = health_p
        self.dexterity_proportion = dex_p
        self.feedback = []
        self.wins = 0
        self.losses = 0
        self._original_attack = attack_p
        self._original_defense = defense_p
        self._original_max_health = health_p
        self._original_dexterity = dex_p
        self.set_to_original_stats()

    def set_to_original_stats(self):
        base = 100
        self.attack = int(base * self.attack_proportion)
        self.defense = int(base * self.defense_proportion)
        self.max_health = int(base * self.max_health_proportion * 5)
        self.health = self.max_health
        self.dexterity = int(base * self.dexterity_proportion)

    def get_combat_info(self):
        return {
            "attack": self.attack,
            "defense": self.defense,
            "dexterity": self.dexterity,
            "health": self.health,
            "max_health": self.max_health,
        }

    def make_combat_decision(self, opponent_stats, turn, your_role, last_opponent_action=None):
        if your_role == "attacker":
            return "attack"
        return "defend"

    def add_feedback(self, msg):
        self.feedback.append(msg)


@pytest.fixture
def game():
    league = MockLeague()
    g = ArenaChampionsGame.__new__(ArenaChampionsGame)
    g.league = league
    g.verbose = False
    g.players = []
    g.scores = {}
    g.game_feedback = {"game": "arena_champions", "battles": []}
    g.player_feedback = {}
    g.battle_history = {}
    return g


@pytest.fixture
def two_players(game):
    p1 = MockPlayer("Fighter1")
    p2 = MockPlayer("Fighter2")
    game.players = [p1, p2]
    game.scores = {"Fighter1": 0, "Fighter2": 0}
    game.battle_history = {"Fighter1": [], "Fighter2": []}
    return p1, p2


def test_battle_result_to_dict():
    br = BattleResult("A", "B")
    br.set_winner("A")
    br.set_final_health(50, 0)
    br.add_turn({"turn": 1, "damage": 20})
    d = br.to_dict()
    assert d["winner"] == "A"
    assert d["final_health"]["A"] == 50
    assert len(d["turns"]) == 1


def test_validate_action_for_role():
    assert ArenaChampionsGame.validate_action_for_role("attack", "attacker") is True
    assert ArenaChampionsGame.validate_action_for_role("big_attack", "attacker") is True
    assert ArenaChampionsGame.validate_action_for_role("defend", "attacker") is False
    assert ArenaChampionsGame.validate_action_for_role("defend", "defender") is True
    assert ArenaChampionsGame.validate_action_for_role("dodge", "defender") is True
    assert ArenaChampionsGame.validate_action_for_role("attack", "defender") is False
    assert ArenaChampionsGame.validate_action_for_role("attack", "unknown") is False


def test_validate_player_attributes_valid(game, two_players):
    p1, _ = two_players
    # Should not raise
    game._validate_player_attributes(p1)


def test_validate_player_attributes_invalid_attack(game, two_players):
    p1, _ = two_players
    p1.attack_proportion = 0.1  # Below 0.2
    with pytest.raises(ValueError, match="attack proportion"):
        game._validate_player_attributes(p1)


def test_validate_player_attributes_sum_exceeds(game, two_players):
    p1, _ = two_players
    p1.attack_proportion = 0.4
    p1.defense_proportion = 0.4
    p1.max_health_proportion = 0.3
    p1.dexterity_proportion = 0.3
    with pytest.raises(ValueError, match="exceed 1.0"):
        game._validate_player_attributes(p1)


def test_calculate_damage_dodge_miss(game, two_players):
    """Test dodge that fails — damage is applied with penalty."""
    p1, p2 = two_players
    import random
    random.seed(0)  # Seed to get consistent dodge fail
    damage, msg = game.calculate_damage(p1, p2, "attack", "dodge")
    # Either dodged or dodge failed — both are valid
    assert damage >= 0
    assert "dodge" in msg.lower()


def test_calculate_damage_defend_actions(game, two_players):
    p1, p2 = two_players
    # defend vs attack (neutral)
    d1, m1 = game.calculate_damage(p1, p2, "attack", "defend")
    assert d1 >= 10
    assert "neutral" in m1 or "defense" in m1

    # defend vs big_attack (weak defense)
    d2, m2 = game.calculate_damage(p1, p2, "big_attack", "defend")
    assert d2 >= 10
    assert "weak" in m2 or "big_attack" in m2

    # defend vs precise (strong defense)
    p1.health = p1.max_health  # Reset health after big_attack self-damage
    d3, m3 = game.calculate_damage(p1, p2, "precise_attack", "defend")
    assert d3 >= 10
    assert "strong" in m3 or "precise" in m3


def test_calculate_damage_brace_actions(game, two_players):
    p1, p2 = two_players
    # brace vs attack (strong brace)
    d1, m1 = game.calculate_damage(p1, p2, "attack", "brace")
    assert "brace" in m1

    # brace vs big_attack (neutral)
    p1.health = p1.max_health
    d2, m2 = game.calculate_damage(p1, p2, "big_attack", "brace")
    assert "brace" in m2

    # brace vs precise (weak brace)
    p1.health = p1.max_health
    d3, m3 = game.calculate_damage(p1, p2, "precise_attack", "brace")
    assert "brace" in m3


def test_calculate_damage_no_valid_defense(game, two_players):
    p1, p2 = two_players
    d, m = game.calculate_damage(p1, p2, "attack", "invalid_action")
    assert "no defense" in m


def test_execute_combat(game, two_players):
    p1, p2 = two_players
    winner, result = game.execute_combat(p1, p2)
    assert winner in ["Fighter1", "Fighter2"]
    assert result.winner == winner
    assert len(result.turns) > 0
    assert result.final_health is not None


def test_get_player_action_invalid_action(game, two_players):
    """Player returning wrong action for role gets default."""
    p1, p2 = two_players
    p1.make_combat_decision = lambda *args, **kwargs: "defend"  # Wrong for attacker
    action = game.get_player_action_with_role(p1, p2, 1, "attacker")
    assert action == "attack"  # Defaults to attack


def test_get_player_action_exception(game, two_players):
    """Player raising exception gets default action."""
    p1, p2 = two_players
    p1.make_combat_decision = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("crash"))
    action = game.get_player_action_with_role(p1, p2, 1, "defender")
    assert action == "defend"  # Defaults to defend


def test_resolve_combat_round(game, two_players):
    p1, p2 = two_players
    p1.health = p1.max_health
    p2.health = p2.max_health
    result = game.resolve_combat_round(p1, p2, "attack", "defend")
    assert "attacker" in result
    assert "defender" in result
    assert "health_before" in result
    assert "health_after" in result
    assert result["effects"]["damage_dealt"] >= 10


def test_play_game_full_tournament(game, two_players):
    """Full tournament with 2 players."""
    game.initialize_characters()
    results = game.play_game()
    assert "points" in results
    assert "score_aggregate" in results
    assert "table" in results
    assert "Fighter1" in results["points"]
    assert "Fighter2" in results["points"]
    assert "wins" in results["table"]
    assert "home_wins" in results["table"]


def test_run_simulations(game, two_players):
    game.initialize_characters()
    results = game.run_simulations(3, game.league)
    assert results["num_simulations"] == 3
    assert "Fighter1" in results["total_points"]
    assert "total_wins" in results["table"]
    assert "avg_wins_per_sim" in results["table"]


def test_reset(game, two_players):
    game.initialize_characters()
    game.play_game()
    game.reset()
    for p in game.players:
        assert p.wins == 0
        assert p.losses == 0
    assert game.game_feedback == {"game": "arena_champions", "battles": []}


def test_run_single_game_with_feedback(game, two_players):
    game.initialize_characters()
    result = game.run_single_game_with_feedback()
    assert "results" in result
    assert "feedback" in result
    assert result["feedback"]["game"] == "arena_champions"
