from datetime import datetime, timedelta

import pytest

from backend.database.db_models import League
from backend.games.breakthrough.breakthrough import DEFAULT_REWARDS, BreakthroughGame
from backend.games.breakthrough.player import Player


@pytest.fixture
def test_league():
    return League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="breakthrough",
    )


@pytest.fixture
def game(test_league):
    return BreakthroughGame(test_league)


@pytest.fixture
def small_game(test_league):
    """A 10x10 board with a short move cap for fast, deterministic matches."""
    g = BreakthroughGame(test_league)
    g.grid_size = 10
    g.move_cap = 20
    return g


class Scripted(Player):
    """Plays a fixed list of moves, repeating the last one forever."""

    def __init__(self, moves, name="Scripted"):
        super().__init__()
        self.name = name
        self.moves = list(moves)
        self.index = 0

    def make_decision(self, game_state):
        move = self.moves[min(self.index, len(self.moves) - 1)]
        self.index += 1
        return move


class Exploder(Player):
    def make_decision(self, game_state):
        raise RuntimeError("boom")


def play(game, attacker_moves, defender_moves, start, rewards=None):
    attacker = Scripted(attacker_moves, name="A")
    defender = Scripted(defender_moves, name="D")
    rewards = game._validate_rewards(rewards)
    return game.play_match(attacker, defender, rewards, start_positions=start)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def test_game_initialization(game):
    assert len(game.players) > 0  # validation players loaded
    assert game.game_feedback == {"game": "breakthrough", "matches": []}
    assert game.grid_size == 100
    assert game.move_cap == 1000
    assert game.attacker_boosts == 5
    assert game.defender_boosts == 10


def test_validation_players_have_strategies(game):
    strategies = game.get_player_strategies()
    assert len(strategies) == len(game.players)


# ---------------------------------------------------------------------------
# Move normalization / resolution
# ---------------------------------------------------------------------------


def test_normalize_move_accepts_string_and_dict(game):
    assert game._normalize_move("E") == ("E", False)
    assert game._normalize_move({"direction": "N", "boost": True}) == ("N", True)
    assert game._normalize_move({"direction": "W"}) == ("W", False)


def test_normalize_move_rejects_garbage(game):
    assert game._normalize_move("X") is None
    assert game._normalize_move(None) is None
    assert game._normalize_move(42) is None
    assert game._normalize_move({"direction": "Q", "boost": True}) is None


def test_normalize_move_stay_never_boosts(game):
    assert game._normalize_move({"direction": "STAY", "boost": True}) == ("STAY", False)


def test_resolve_move_off_grid_stays(game):
    assert game._resolve_move((0, 50), "W", False, 5) == ((0, 50), False)
    assert game._resolve_move((0, 99), "N", False, 5) == ((0, 99), False)
    # Boost that would land off-grid also stays and keeps the boost
    assert game._resolve_move((0, 98), "N", True, 5) == ((0, 98), False)


def test_resolve_move_boost_without_stock_stays(game):
    assert game._resolve_move((5, 5), "E", True, 0) == ((5, 5), False)


def test_resolve_move_boost_jumps_two(game):
    assert game._resolve_move((5, 5), "E", True, 1) == ((7, 5), True)


# ---------------------------------------------------------------------------
# Catch rules
# ---------------------------------------------------------------------------


def test_same_cell_catch(small_game):
    # Attacker (0,5) moves E, defender (2,5) moves W -> both on (1,5)
    match, _, _ = play(small_game, ["E"], ["W"], start=((0, 5), (2, 5)))
    assert match["result"] == "caught"
    assert match["end_turn"] == 1
    assert match["final"]["a"] == match["final"]["d"] == [1, 5]


def test_swap_catch(small_game):
    # Adjacent players move through each other
    match, _, _ = play(small_game, ["E"], ["W"], start=((0, 5), (1, 5)))
    assert match["result"] == "caught"
    assert match["end_turn"] == 1


def test_boost_jump_over_defender_is_safe(small_game):
    # Attacker boosts from (0,5) over the stationary defender at (1,5), lands (2,5)
    match, _, _ = play(
        small_game,
        [{"direction": "E", "boost": True}, "E"],
        ["STAY"],
        start=((0, 5), (1, 5)),
    )
    assert match["result"] == "breakthrough"  # sails to x=9 unopposed
    assert match["end_turn"] == 8  # jump to 2, then 7 single steps


def test_boost_landing_on_defender_end_cell_is_catch(small_game):
    # Attacker boosts (0,5)->(2,5); defender stays on (2,5)
    match, _, _ = play(
        small_game,
        [{"direction": "E", "boost": True}],
        ["STAY"],
        start=((0, 5), (2, 5)),
    )
    assert match["result"] == "caught"
    assert match["end_turn"] == 1


def test_catch_takes_precedence_over_breakthrough(small_game):
    # Attacker steps onto the goal column but the defender meets them there
    match, _, _ = play(small_game, ["E"], ["W"], start=((8, 5), (9, 5)))
    assert match["result"] == "caught"


# ---------------------------------------------------------------------------
# Outcomes and scoring
# ---------------------------------------------------------------------------


def test_breakthrough_and_scoring(small_game):
    # Unopposed attacker walks from x=0 to x=9 in 9 turns
    match, a_score, d_score = play(small_game, ["E"], ["STAY"], start=((0, 5), (5, 0)))
    assert match["result"] == "breakthrough"
    assert match["end_turn"] == 9
    assert a_score == pytest.approx(100 + 100 * (20 - 9) / 20)
    assert d_score == pytest.approx(100 * 9 / 20)


def test_caught_scoring(small_game):
    # Caught on turn 1 at x=1: defender survival + bonus, attacker progress
    _, a_score, d_score = play(small_game, ["E"], ["W"], start=((0, 5), (2, 5)))
    assert d_score == pytest.approx(100 * 1 / 20 + 100)
    assert a_score == pytest.approx(50 * 1 / 9)


def test_timeout_scoring(small_game):
    small_game.move_cap = 5
    match, a_score, d_score = play(small_game, ["STAY"], ["STAY"], start=((3, 5), (7, 5)))
    assert match["result"] == "timeout"
    assert match["end_turn"] == 5
    assert d_score == pytest.approx(100)
    assert a_score == pytest.approx(50 * 3 / 9)  # furthest_x is the start column


def test_catch_always_beats_timeout(small_game):
    # An early catch must still outscore a full timeout for the defender
    _, _, catch_score = play(small_game, ["E"], ["W"], start=((0, 5), (2, 5)))
    assert catch_score > 100


def test_custom_rewards(small_game):
    rewards = [10, 20, 30, 40, 5]
    _, a_score, d_score = play(
        small_game, ["E"], ["W"], start=((0, 5), (2, 5)), rewards=rewards
    )
    assert d_score == pytest.approx(10 * 1 / 20 + 20)
    assert a_score == pytest.approx(5 * 1 / 9)


def test_invalid_custom_rewards_fall_back_to_default(game):
    assert game._validate_rewards(None) == [float(v) for v in DEFAULT_REWARDS]
    assert game._validate_rewards([1, 2]) == [float(v) for v in DEFAULT_REWARDS]
    assert game._validate_rewards(["a", 1, 2, 3, 4]) == [float(v) for v in DEFAULT_REWARDS]
    assert game._validate_rewards([1, 2, 3, 4, 5]) == [1.0, 2.0, 3.0, 4.0, 5.0]


# ---------------------------------------------------------------------------
# Boost accounting / robustness
# ---------------------------------------------------------------------------


def test_boost_stock_depletes(small_game):
    small_game.attacker_boosts = 1
    small_game.move_cap = 3
    boost_e = {"direction": "E", "boost": True}
    match, _, _ = play(small_game, [boost_e, boost_e, "STAY"], ["STAY"], start=((0, 5), (9, 0)))
    # First boost jumps to x=2; second has no stock so resolves to STAY
    assert match["final"]["a"] == [2, 5]


def test_exception_in_make_decision_is_stay(small_game, test_league):
    small_game.move_cap = 4
    attacker = Exploder()
    attacker.name = "A"
    defender = Scripted(["STAY"], name="D")
    match, _, _ = small_game.play_match(
        attacker, defender, small_game._validate_rewards(None), start_positions=((0, 5), (9, 0))
    )
    assert match["result"] == "timeout"
    assert match["final"]["a"] == [0, 5]


def test_traces_and_state_shape(small_game):
    seen = {}

    class Recorder(Player):
        def make_decision(self, game_state):
            seen.update(game_state)
            return "E"

    attacker = Recorder()
    attacker.name = "A"
    defender = Scripted(["STAY"], name="D")
    small_game.play_match(
        attacker, defender, small_game._validate_rewards(None), start_positions=((0, 5), (5, 0))
    )
    for key in (
        "turn", "role", "my_pos", "opp_pos", "my_boosts", "opp_boosts",
        "my_trace", "opp_trace", "grid_size", "move_cap",
    ):
        assert key in seen
    assert seen["role"] == "attacker"
    assert seen["my_trace"][0] == (0, 5)
    assert len(seen["my_trace"]) > 1  # trail grew as the attacker moved


# ---------------------------------------------------------------------------
# Tournament structure
# ---------------------------------------------------------------------------


def test_play_game_structure(small_game):
    small_game.move_cap = 30
    results = small_game.play_game()
    names = {str(p.name) for p in small_game.players}
    assert set(results["points"].keys()) == names
    assert set(results["table"].keys()) == {
        "matches_played", "wins", "catches", "breakthroughs",
    }
    n = len(names)
    # Every pairing plays twice (once per role)
    assert sum(results["table"]["matches_played"].values()) == n * (n - 1) * 2
    assert sum(results["table"]["wins"].values()) == n * (n - 1)


def test_verbose_game_records_matches(small_game):
    small_game.move_cap = 30
    small_game.verbose = True
    small_game.play_game()
    matches = small_game.game_feedback["matches"]
    n = len(small_game.players)
    assert len(matches) == n * (n - 1)
    for match in matches:
        assert match["result"] in ("caught", "breakthrough", "timeout")
        assert len(match["turns"]) == match["end_turn"]
        assert set(match["scores"].keys()) == {match["attacker"], match["defender"]}


def test_run_simulations_caps_total_matches(small_game):
    small_game.move_cap = 30
    results = small_game.run_simulations(10000, None)
    assert results["num_simulations"] <= 1000
    assert set(results["table"].keys()) == {
        "wins", "games_played", "catches", "breakthroughs",
    }
    names = {str(p.name) for p in small_game.players}
    assert set(results["total_points"].keys()) == names


def test_starter_code_runs_as_submitted_agent(small_game):
    small_game.move_cap = 50
    player = small_game.add_player(BreakthroughGame.starter_code, "StarterBot")
    assert player is not None
    results = small_game.play_game()
    assert "StarterBot" in results["points"]
    assert results["table"]["matches_played"]["StarterBot"] == 2 * len(
        small_game.players
    ) - 2
    assert results["points"]["StarterBot"] > 0


def test_reset_restores_feedback_shape(small_game):
    small_game.verbose = True
    small_game.move_cap = 30
    small_game.play_game()
    small_game.reset()
    assert small_game.game_feedback == {"game": "breakthrough", "matches": []}
    assert small_game.player_feedback == {}
    assert len(small_game.players) > 0
