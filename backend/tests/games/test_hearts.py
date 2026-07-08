import random
from datetime import timedelta

import pytest

from backend.database.db_models import League
from backend.games.hearts.hearts import (
    DECK,
    DEFAULT_REWARDS,
    HeartsGame,
    TableScheduler,
    card_points,
    card_suit,
    sort_hand,
)
from backend.games.hearts.player import Player
from backend.time_utils import utc_now


@pytest.fixture
def test_league():
    return League(
        name="test_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="hearts",
    )


class LowCard(Player):
    """Minimal deterministic legal player for tests."""

    def make_decision(self, game_state):
        if game_state["phase"] == "pass":
            return game_state["hand"][:3]
        return game_state["legal_moves"][0]


class Broken(Player):
    def make_decision(self, game_state):
        raise RuntimeError("boom")


def _add_players(game, n, cls=LowCard):
    for i in range(n):
        p = cls()
        p.name = f"{cls.__name__}_{i}"
        game.players.append(p)
        game.scores[p.name] = 0


# ---------------------------------------------------------------- deck/rules


def test_deck_is_full_52():
    assert len(DECK) == 52
    assert len(set(DECK)) == 52
    assert sum(card_points(c) for c in DECK) == 26


def test_game_initialization(test_league):
    game = HeartsGame(test_league)
    assert len(game.players) == 8  # validation players
    assert game.game_feedback == {"game": "hearts", "hands": []}


def test_legal_moves_first_trick_must_lead_2c(test_league):
    game = HeartsGame(test_league)
    hand = ["2C", "AH", "QS", "5D"]
    assert game._legal_moves(hand, [], True, False) == ["2C"]


def test_legal_moves_follow_suit(test_league):
    game = HeartsGame(test_league)
    hand = ["5C", "AH", "QS"]
    trick = [{"player": "x", "card": "2C"}]
    assert game._legal_moves(hand, trick, False, False) == ["5C"]


def test_legal_moves_no_points_on_first_trick_when_void(test_league):
    game = HeartsGame(test_league)
    hand = ["AH", "QS", "5D"]
    trick = [{"player": "x", "card": "2C"}]
    assert game._legal_moves(hand, trick, True, False) == ["5D"]


def test_legal_moves_hearts_not_led_until_broken(test_league):
    game = HeartsGame(test_league)
    hand = ["AH", "5D"]
    assert game._legal_moves(hand, [], False, False) == ["5D"]
    assert set(game._legal_moves(hand, [], False, True)) == {"AH", "5D"}
    # only hearts left: may lead them even unbroken
    assert game._legal_moves(["AH", "2H"], [], False, False) == ["AH", "2H"]


def test_placement_points_ties_share_mean():
    scores = {"a": 10, "b": 10, "c": 50, "d": 90}
    pts = HeartsGame._placement_points(scores, DEFAULT_REWARDS)
    assert pts == {"a": 3.0, "b": 3.0, "c": 1, "d": 0}


# ------------------------------------------------------------- table games


def test_full_table_game_terminates_and_scores(test_league):
    game = HeartsGame(test_league)
    game.players = []
    _add_players(game, 4)
    scores, winner, stats, _ = game._play_table_game(
        game.players, random.Random(0), verbose=False
    )
    assert max(scores.values()) >= HeartsGame.TARGET_SCORE
    assert winner == min(scores, key=scores.get)
    assert stats["hands"] <= HeartsGame.MAX_HANDS
    # every hand distributes 26 points (or 78 on a moon)
    total = sum(scores.values())
    moons = sum(stats["moons"].values())
    assert total == 26 * (stats["hands"] - moons) + 78 * moons


def test_broken_agent_raises_value_error(test_league):
    game = HeartsGame(test_league)
    game.players = []
    _add_players(game, 3)
    _add_players(game, 1, Broken)
    with pytest.raises(ValueError, match="Invalid"):
        game._play_table_game(game.players, random.Random(0), verbose=False)


# ------------------------------------------------------------- tournaments


def test_play_game_four_players_one_game_per_call(test_league):
    game = HeartsGame(test_league)
    game.players = []
    _add_players(game, 4)
    result = game.play_game()
    assert result is not None
    assert set(result["points"].keys()) == {p.name for p in game.players}
    # one game: placement points sum to the reward pool
    assert sum(result["points"].values()) == pytest.approx(sum(DEFAULT_REWARDS))
    assert result["table"]["games_played"] == {p.name: 1 for p in game.players}


def test_play_game_exhaustive_covers_all_groups(test_league):
    game = HeartsGame(test_league)
    game.players = []
    _add_players(game, 5)
    result = game.play_game()
    # C(5,4) = 5 games; each player sits out exactly one
    assert result["table"]["games_played"] == {p.name: 4 for p in game.players}
    total = sum(result["table"]["games_played"].values())
    assert total / 4 == 5


def test_play_game_survives_reset_between_calls(test_league):
    game = HeartsGame(test_league)
    game.players = []
    _add_players(game, 4)
    game.play_game()
    game.reset()
    result = game.play_game()
    assert result["table"]["games_played"] == {p.name: 2 for p in game.players}


def test_points_deltas_telescope_to_window_total(test_league):
    game = HeartsGame(test_league)
    game.players = []
    _add_players(game, 4)
    running = {p.name: 0.0 for p in game.players}
    for _ in range(5):
        result = game.play_game()
        for n, pts in result["points"].items():
            running[n] += pts
    state = game._tournament
    for n in running:
        assert running[n] == pytest.approx(sum(state["recent"][n]))


def test_roster_pads_short_leagues_with_validation_players(test_league):
    game = HeartsGame(test_league)
    game.players = []
    _add_players(game, 2)
    roster = game._roster()
    assert len(roster) == 4
    assert {type(p).__name__ for p in roster[2:]} <= {
        "RandomBot",
        "LowballBot",
        "MoonShooter",
        "QueenDumper",
        "HeartAvoider",
        "TrickDucker",
        "VoidMaker",
        "Cautious",
    }


def test_scheduler_mode_for_large_player_counts(test_league):
    game = HeartsGame(test_league)
    game.players = []
    _add_players(game, 21 + 4)  # > EXHAUSTIVE_MAX_PLAYERS
    state = game._ensure_tournament()
    assert not state["exhaustive"]
    result = game.play_game()
    played = result["table"]["games_played"]
    # 5 rounds of 6 disjoint tables, byes rotate: everyone plays 4-5 games
    assert set(played.values()) <= {4, 5}
    assert sum(played.values()) == 4 * 6 * HeartsGame.SCHEDULER_ROUNDS_PER_CALL


def test_scheduler_round_tables_are_disjoint():
    rng = random.Random(1)
    sched = TableScheduler([f"p{i}" for i in range(14)], rng)
    tables = sched.next_round()
    seated = [p for t in tables for p in t]
    assert len(seated) == len(set(seated)) == 12  # 14 -> 2 byes
    assert all(len(t) == 4 for t in tables)


def test_run_simulations_shape(test_league):
    game = HeartsGame(test_league)
    game.players = []
    _add_players(game, 4)
    results = game.run_simulations(10, test_league)
    assert set(results.keys()) == {"total_points", "num_simulations", "table"}
    assert results["num_simulations"] == 10
    for key in ("games_won", "avg_points_per_hand", "moons_shot", "queens_taken"):
        assert set(results["table"][key].keys()) == {p.name for p in game.players}


# --------------------------------------------------------------- feedback


def test_run_single_game_with_feedback_contract(test_league):
    game = HeartsGame(test_league)
    game.players = []
    _add_players(game, 4)
    out = game.run_single_game_with_feedback()
    fb = out["feedback"]
    assert fb["game"] == "hearts"
    assert fb["target_score"] == HeartsGame.TARGET_SCORE
    assert fb["winner"] == min(fb["final_scores"], key=fb["final_scores"].get)
    assert len(fb["players"]) == 4
    for hand in fb["hands"]:
        assert set(hand.keys()) == {
            "hand_number",
            "pass_direction",
            "dealt_hands",
            "passes",
            "hands_after_pass",
            "tricks",
            "hand_scores",
            "shot_the_moon",
            "running_scores",
        }
        assert len(hand["tricks"]) == 13
        for trick in hand["tricks"]:
            assert len(trick["plays"]) == 4
        # all 52 cards dealt
        dealt = [c for cards in hand["dealt_hands"].values() for c in cards]
        assert sorted(dealt) == sorted(DECK)
        if hand["pass_direction"] == "hold":
            assert hand["passes"] is None
        else:
            assert all(len(p["cards"]) == 3 for p in hand["passes"].values())
        # first trick led with 2C
        assert hand["tricks"][0]["plays"][0]["card"] == "2C"


def test_feedback_follows_suit_everywhere(test_league):
    """Replay the feedback log and verify every play was legal."""
    game = HeartsGame(test_league)
    game.players = []
    _add_players(game, 4)
    fb = game.run_single_game_with_feedback()["feedback"]
    for hand in fb["hands"]:
        held = {n: list(cs) for n, cs in hand["hands_after_pass"].items()}
        for trick in hand["tricks"]:
            led = card_suit(trick["plays"][0]["card"])
            for play in trick["plays"]:
                n, card = play["player"], play["card"]
                assert card in held[n]
                if card_suit(card) != led:
                    assert not any(card_suit(c) == led for c in held[n]), (
                        f"{n} revoked: played {card} while holding {led}"
                    )
                held[n].remove(card)


def test_add_player_with_starter_code(test_league):
    game = HeartsGame(test_league)
    player = game.add_player(HeartsGame.starter_code, "TestTeam")
    assert player is not None
    assert len(game.players) == 9  # 8 validation players + the added team
    result = game.play_game()
    assert "TestTeam" in result["points"]


def test_sort_hand_groups_suits():
    hand = ["AH", "2C", "QS", "10D", "3C"]
    assert sort_hand(hand) == ["2C", "3C", "10D", "QS", "AH"]
