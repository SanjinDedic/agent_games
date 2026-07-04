import random
from datetime import datetime, timedelta

import pytest

from backend.database.db_models import League
from backend.games.ohhell.ohhell import (
    DEAL_SEQUENCE,
    DECK,
    DEFAULT_REWARDS,
    OhHellGame,
    TABLE_SIZE,
    TableScheduler,
    card_suit,
    sort_hand,
)
from backend.games.ohhell.player import Player


@pytest.fixture
def test_league():
    return League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="ohhell",
    )


class LowCard(Player):
    """Minimal deterministic legal player: bids 0 (or 1 when 0 is forbidden),
    always plays its first legal card."""

    def make_decision(self, game_state):
        if game_state["phase"] == "bid":
            return 1 if game_state["forbidden_bid"] == 0 else 0
        return game_state["legal_moves"][0]


class FixedBid(Player):
    def __init__(self, bid):
        super().__init__()
        self._bid = bid

    def make_decision(self, game_state):
        if game_state["phase"] == "bid":
            return self._bid
        return game_state["legal_moves"][0]


class Broken(Player):
    def make_decision(self, game_state):
        raise RuntimeError("boom")


def _add_players(game, n, cls=LowCard):
    for i in range(n):
        p = cls() if cls is not FixedBid else cls(0)
        p.name = f"{cls.__name__}_{i}"
        game.players.append(p)
        game.scores[p.name] = 0


# ---------------------------------------------------------------- deck/rules


def test_deck_is_full_52():
    assert len(DECK) == 52
    assert len(set(DECK)) == 52


def test_deal_sequence_fits_four_players():
    # Every round must leave at least one card in the stub to flip for trump.
    assert DEAL_SEQUENCE == sorted(DEAL_SEQUENCE, reverse=True)
    assert max(DEAL_SEQUENCE) * TABLE_SIZE < len(DECK)
    assert min(DEAL_SEQUENCE) == 1


def test_game_initialization(test_league):
    game = OhHellGame(test_league)
    assert len(game.players) == 5  # validation players
    assert game.game_feedback == {"game": "ohhell", "rounds": []}


def test_legal_moves_leading_is_unrestricted(test_league):
    game = OhHellGame(test_league)
    hand = ["2C", "AH", "QS", "5D"]
    assert game._legal_moves(hand, []) == hand  # trump need not be broken


def test_legal_moves_follow_suit(test_league):
    game = OhHellGame(test_league)
    hand = ["5C", "AH", "QS"]
    trick = [{"player": "x", "card": "2C"}]
    assert game._legal_moves(hand, trick) == ["5C"]


def test_legal_moves_void_plays_anything(test_league):
    game = OhHellGame(test_league)
    hand = ["AH", "QS", "5D"]
    trick = [{"player": "x", "card": "2C"}]
    assert game._legal_moves(hand, trick) == hand


def test_trick_winner_highest_of_led_suit(test_league):
    game = OhHellGame(test_league)
    plays = [
        {"player": "a", "card": "2C"},
        {"player": "b", "card": "KC"},
        {"player": "c", "card": "5C"},
        {"player": "d", "card": "AD"},  # off suit, not trump
    ]
    assert game._trick_winner(plays, "S") == "b"


def test_trick_winner_trump_beats_led(test_league):
    game = OhHellGame(test_league)
    plays = [
        {"player": "a", "card": "AC"},  # led clubs, high
        {"player": "b", "card": "KC"},
        {"player": "c", "card": "2S"},  # trump
        {"player": "d", "card": "5C"},
    ]
    assert game._trick_winner(plays, "S") == "c"


def test_trick_winner_highest_trump(test_league):
    game = OhHellGame(test_league)
    plays = [
        {"player": "a", "card": "AC"},
        {"player": "b", "card": "2S"},  # trump
        {"player": "c", "card": "QS"},  # higher trump
        {"player": "d", "card": "5C"},
    ]
    assert game._trick_winner(plays, "S") == "c"


def test_placement_points_highest_wins_ties_share_mean():
    # Highest Oh Hell score is best. a and b tie for the top two placements.
    scores = {"a": 50, "b": 50, "c": 30, "d": 5}
    pts = OhHellGame._placement_points(scores, DEFAULT_REWARDS)
    assert pts == {"a": 3.0, "b": 3.0, "c": 1, "d": 0}


# --------------------------------------------------------------- bidding


def _bid_args(game, player, cards, forbidden):
    hand = ["AH", "KH", "2C"][:cards] or ["AH"]
    return game._ask_bid(
        player, hand, "H", "7H", cards, 1, [], forbidden, "d", {}, ["a", "b", "c", "d"]
    )


def test_ask_bid_rejects_out_of_range(test_league):
    game = OhHellGame(test_league)
    with pytest.raises(ValueError, match="Invalid bid"):
        _bid_args(game, FixedBid(5), 3, None)


def test_ask_bid_rejects_forbidden(test_league):
    game = OhHellGame(test_league)
    with pytest.raises(ValueError, match="forbidden"):
        _bid_args(game, FixedBid(2), 3, 2)


def test_ask_bid_accepts_valid(test_league):
    game = OhHellGame(test_league)
    assert _bid_args(game, FixedBid(1), 3, 2) == 1


# ------------------------------------------------------------- table games


def test_full_table_game_terminates_and_scores(test_league):
    game = OhHellGame(test_league)
    game.players = []
    _add_players(game, 4)
    scores, winner, stats, _ = game._play_table_game(
        game.players, random.Random(0), verbose=False
    )
    assert stats["rounds"] == len(DEAL_SEQUENCE)
    assert winner == max(scores, key=scores.get)
    assert all(v >= 0 for v in scores.values())
    # bids_hit can never exceed the number of rounds played
    assert all(0 <= h <= stats["rounds"] for h in stats["bids_hit"].values())


def test_broken_agent_raises_value_error(test_league):
    game = OhHellGame(test_league)
    game.players = []
    _add_players(game, 3)
    _add_players(game, 1, Broken)
    with pytest.raises(ValueError, match="Invalid"):
        game._play_table_game(game.players, random.Random(0), verbose=False)


# ------------------------------------------------------------- tournaments


def test_play_game_four_players_one_game_per_call(test_league):
    game = OhHellGame(test_league)
    game.players = []
    _add_players(game, 4)
    result = game.play_game()
    assert result is not None
    assert set(result["points"].keys()) == {p.name for p in game.players}
    assert sum(result["points"].values()) == pytest.approx(sum(DEFAULT_REWARDS))
    assert result["table"]["games_played"] == {p.name: 1 for p in game.players}


def test_play_game_exhaustive_covers_all_groups(test_league):
    game = OhHellGame(test_league)
    game.players = []
    _add_players(game, 5)
    result = game.play_game()
    assert result["table"]["games_played"] == {p.name: 4 for p in game.players}
    assert sum(result["table"]["games_played"].values()) / 4 == 5


def test_play_game_survives_reset_between_calls(test_league):
    game = OhHellGame(test_league)
    game.players = []
    _add_players(game, 4)
    game.play_game()
    game.reset()
    result = game.play_game()
    assert result["table"]["games_played"] == {p.name: 2 for p in game.players}


def test_points_deltas_telescope_to_window_total(test_league):
    game = OhHellGame(test_league)
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
    game = OhHellGame(test_league)
    game.players = []
    _add_players(game, 2)
    roster = game._roster()
    assert len(roster) == 4
    assert {type(p).__name__ for p in roster[2:]} <= {
        "Estimator",
        "AceCounter",
        "ZeroBidder",
        "RandomBot",
        "GreedyBidder",
    }


def test_scheduler_mode_for_large_player_counts(test_league):
    game = OhHellGame(test_league)
    game.players = []
    _add_players(game, 21 + 4)  # > EXHAUSTIVE_MAX_PLAYERS
    state = game._ensure_tournament()
    assert not state["exhaustive"]
    result = game.play_game()
    played = result["table"]["games_played"]
    assert set(played.values()) <= {4, 5}
    assert sum(played.values()) == 4 * 6 * OhHellGame.SCHEDULER_ROUNDS_PER_CALL


def test_scheduler_round_tables_are_disjoint():
    rng = random.Random(1)
    sched = TableScheduler([f"p{i}" for i in range(14)], rng)
    tables = sched.next_round()
    seated = [p for t in tables for p in t]
    assert len(seated) == len(set(seated)) == 12  # 14 -> 2 byes
    assert all(len(t) == 4 for t in tables)


def test_run_simulations_shape(test_league):
    game = OhHellGame(test_league)
    game.players = []
    _add_players(game, 4)
    results = game.run_simulations(10, test_league)
    assert set(results.keys()) == {"total_points", "num_simulations", "table"}
    assert results["num_simulations"] == 10
    for key in ("games_won", "bid_accuracy", "avg_round_score"):
        assert set(results["table"][key].keys()) == {p.name for p in game.players}


# --------------------------------------------------------------- feedback


def test_run_single_game_with_feedback_contract(test_league):
    game = OhHellGame(test_league)
    game.players = []
    _add_players(game, 4)
    out = game.run_single_game_with_feedback()
    fb = out["feedback"]
    assert fb["game"] == "ohhell"
    assert fb["winner"] == max(fb["final_scores"], key=fb["final_scores"].get)
    assert len(fb["players"]) == 4
    assert len(fb["rounds"]) == len(DEAL_SEQUENCE)
    for rnd in fb["rounds"]:
        assert set(rnd.keys()) == {
            "round_number",
            "cards",
            "trump",
            "trump_card",
            "dealer",
            "dealt_hands",
            "bids",
            "tricks",
            "tricks_won",
            "round_scores",
            "running_scores",
        }
        assert len(rnd["tricks"]) == rnd["cards"]
        for trick in rnd["tricks"]:
            assert len(trick["plays"]) == 4
        # `cards` are dealt to each of 4 players; the trump card is a separate flip
        dealt = [c for cards in rnd["dealt_hands"].values() for c in cards]
        assert len(dealt) == rnd["cards"] * 4
        assert len(set(dealt)) == len(dealt)
        assert rnd["trump_card"] not in dealt  # flip comes from the stub
        assert card_suit(rnd["trump_card"]) == rnd["trump"]
        # the hook rule guarantees bids can never total the tricks available
        assert sum(rnd["bids"].values()) != rnd["cards"]
        # scoring: 1 point per trick, +10 for hitting the bid exactly
        for p in fb["players"]:
            made = rnd["tricks_won"][p] == rnd["bids"][p]
            assert rnd["round_scores"][p] == rnd["tricks_won"][p] + (10 if made else 0)
        assert sum(rnd["tricks_won"].values()) == rnd["cards"]


def test_feedback_follows_suit_everywhere(test_league):
    """Replay the feedback log and verify every play was legal."""
    game = OhHellGame(test_league)
    game.players = []
    _add_players(game, 4)
    fb = game.run_single_game_with_feedback()["feedback"]
    for rnd in fb["rounds"]:
        held = {n: list(cs) for n, cs in rnd["dealt_hands"].items()}
        for trick in rnd["tricks"]:
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
    game = OhHellGame(test_league)
    player = game.add_player(OhHellGame.starter_code, "TestTeam")
    assert player is not None
    assert len(game.players) == 6  # 5 validation players + the added team
    result = game.play_game()
    assert "TestTeam" in result["points"]


def test_sort_hand_groups_suits():
    hand = ["AH", "2C", "QS", "10D", "3C"]
    assert sort_hand(hand) == ["2C", "3C", "10D", "QS", "AH"]
