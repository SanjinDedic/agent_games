import random
from datetime import timedelta

import pytest

from backend.database.db_models import League
from backend.games.thirteen.player import Player
from backend.games.thirteen.thirteen import (
    DECK,
    DEFAULT_REWARDS,
    RANK_VALUE,
    TABLE_SIZE,
    TableScheduler,
    ThirteenGame,
    beats,
    card_key,
    card_rank,
    classify,
    sort_hand,
)
from backend.time_utils import utc_now


@pytest.fixture
def test_league():
    return League(
        name="test_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="thirteen",
    )


class FirstMove(Player):
    """Deterministic legal player: takes the first legal move — the lowest
    beating combo when answering, or a pass only when nothing beats the pile."""

    def make_decision(self, game_state):
        return game_state["legal_moves"][0]


class PassBot(Player):
    """Passes whenever allowed; otherwise leads its first legal combo."""

    def make_decision(self, game_state):
        if [] in game_state["legal_moves"]:
            return []
        return game_state["legal_moves"][0]


class Broken(Player):
    def make_decision(self, game_state):
        raise RuntimeError("boom")


def _add_players(game, n, cls=FirstMove):
    for i in range(n):
        p = cls()
        p.name = f"{cls.__name__}_{i}"
        game.players.append(p)
        game.scores[p.name] = 0


# ---------------------------------------------------------------- deck/model


def test_deck_is_full_52():
    assert len(DECK) == 52
    assert len(set(DECK)) == 52


def test_rank_and_suit_ordering():
    # 3 is the lowest rank, 2 the highest.
    assert RANK_VALUE["3"] < RANK_VALUE["A"] < RANK_VALUE["2"]
    # 2H is the single strongest card, 3S the weakest.
    assert card_key("2H") == max(card_key(c) for c in DECK)
    assert card_key("3S") == min(card_key(c) for c in DECK)
    # suits break rank ties S < C < D < H
    assert card_key("5S") < card_key("5C") < card_key("5D") < card_key("5H")


def test_sort_hand_orders_by_rank_then_suit():
    hand = ["2H", "3S", "10D", "3C", "AS"]
    assert sort_hand(hand) == ["3S", "3C", "10D", "AS", "2H"]


# ---------------------------------------------------------------- classify


def test_classify_recognises_each_shape():
    assert classify(["7D"]) == ("single", 1, card_key("7D"))
    assert classify(["7D", "7S"])[0] == "pair"
    assert classify(["7D", "7S", "7C"])[0] == "triple"
    assert classify(["7D", "7S", "7C", "7H"])[0] == "bomb"
    straight = classify(["4S", "5C", "6D"])
    assert straight[0] == "straight" and straight[1] == 3
    assert straight[2] == card_key("6D")  # top of the run


def test_classify_rejects_illegal_shapes():
    assert classify([]) is None
    assert classify(["4S", "5S"]) is None  # two different ranks, not a run
    assert classify(["4S", "5C", "7D"]) is None  # non-consecutive
    assert classify(["AS", "2S", "3S"]) is None  # a 2 cannot sit in a straight
    assert classify(["QS", "KS", "AS", "2S"]) is None  # ...even a longer run
    assert classify(["3S", "3S"]) is None  # duplicate card


# ------------------------------------------------------------------- beats


def test_beats_same_shape_higher():
    assert beats(["4S"], ["3S"])
    assert beats(["3H"], ["3S"])  # same rank, higher suit
    assert not beats(["3S"], ["3H"])
    assert beats(["5S", "5C"], ["4D", "4H"])  # higher pair
    assert not beats(["4S", "4C"], ["4D", "4H"])  # equal rank pair does not beat
    assert beats(["6S", "7C", "8D"], ["5S", "6C", "7D"])  # higher run
    assert not beats(["5S", "6C", "7D", "8H"], ["5S", "6C", "7D"])  # length must match


def test_beats_different_shapes_do_not_cross():
    assert not beats(["4S", "4C"], ["3S"])  # pair over single
    assert not beats(["4S"], ["3S", "3C"])  # single over pair


def test_bomb_powers():
    bomb = ["5S", "5C", "5D", "5H"]
    assert beats(bomb, ["2S"])  # chops a single 2
    assert beats(bomb, ["2S", "2C"])  # chops a pair of 2s
    assert not beats(bomb, ["AH"])  # a non-2 single is safe from a bomb
    higher = ["6S", "6C", "6D", "6H"]
    assert beats(higher, bomb)  # higher four-of-a-kind
    assert not beats(bomb, higher)


# ---------------------------------------------------------------- legal moves


def test_legal_leads_enumerates_shapes(test_league):
    game = ThirteenGame(test_league)
    hand = ["3S", "3C", "4S", "5S", "6S"]
    leads = [sorted(m, key=card_key) for m in game._legal_leads(hand)]
    assert ["3S"] in leads
    assert sort_hand(["3S", "3C"]) in leads
    assert sort_hand(["4S", "5S", "6S"]) in leads  # straight
    # every lead is a legal shape
    assert all(classify(m) is not None for m in leads)


def test_legal_responses_includes_pass_and_only_beaters(test_league):
    game = ThirteenGame(test_league)
    hand = ["4S", "4C", "5H", "2H"]
    pile = ["3S"]
    moves = game._legal_responses(hand, pile)
    assert [] in moves  # pass is always offered when responding
    assert all(beats(m, pile) for m in moves if m)
    assert ["4S"] in moves and ["2H"] in moves
    assert not any(len(m) == 2 for m in moves)  # a pair cannot answer a single


def test_legal_responses_bomb_answers_two(test_league):
    game = ThirteenGame(test_league)
    hand = ["6S", "6C", "6D", "6H", "3S"]
    moves = game._legal_responses(hand, ["2S"])
    assert sort_hand(["6S", "6C", "6D", "6H"]) in [sort_hand(m) for m in moves if m]


# ------------------------------------------------------------- table games


def test_full_deal_terminates_and_places_everyone(test_league):
    game = ThirteenGame(test_league)
    game.players = []
    _add_players(game, 4)
    finish_order, winner, stats, _ = game._play_table_game(
        game.players, random.Random(0), verbose=False
    )
    names = {p.name for p in game.players}
    assert set(finish_order) == names
    assert len(finish_order) == len(set(finish_order)) == 4
    assert winner == finish_order[0]
    assert stats["finish_pos"][winner] == 1
    assert sorted(stats["finish_pos"].values()) == [1, 2, 3, 4]


def test_all_passers_still_terminates(test_league):
    game = ThirteenGame(test_league)
    game.players = []
    _add_players(game, 4, PassBot)
    finish_order, _, _, _ = game._play_table_game(
        game.players, random.Random(1), verbose=False
    )
    assert len(finish_order) == 4


def test_broken_agent_raises_value_error(test_league):
    game = ThirteenGame(test_league)
    game.players = []
    _add_players(game, 3)
    _add_players(game, 1, Broken)
    with pytest.raises(ValueError, match="Invalid"):
        game._play_table_game(game.players, random.Random(0), verbose=False)


# --------------------------------------------------------------- scoring


def test_placement_points_follow_finish_order():
    pts = ThirteenGame._placement_points(["a", "b", "c", "d"], DEFAULT_REWARDS)
    assert pts == {"a": 4, "b": 2, "c": 1, "d": 0}


# ------------------------------------------------------------- tournaments


def test_play_game_four_players_one_game_per_call(test_league):
    game = ThirteenGame(test_league)
    game.players = []
    _add_players(game, 4)
    result = game.play_game()
    assert result is not None
    assert set(result["points"].keys()) == {p.name for p in game.players}
    assert sum(result["points"].values()) == pytest.approx(sum(DEFAULT_REWARDS))
    assert result["table"]["games_played"] == {p.name: 1 for p in game.players}


def test_play_game_exhaustive_covers_all_groups(test_league):
    game = ThirteenGame(test_league)
    game.players = []
    _add_players(game, 5)
    result = game.play_game()
    assert result["table"]["games_played"] == {p.name: 4 for p in game.players}
    assert sum(result["table"]["games_played"].values()) / 4 == 5


def test_play_game_survives_reset_between_calls(test_league):
    game = ThirteenGame(test_league)
    game.players = []
    _add_players(game, 4)
    game.play_game()
    game.reset()
    result = game.play_game()
    assert result["table"]["games_played"] == {p.name: 2 for p in game.players}


def test_points_deltas_telescope_to_window_total(test_league):
    game = ThirteenGame(test_league)
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
    game = ThirteenGame(test_league)
    game.players = []
    _add_players(game, 2)
    roster = game._roster()
    assert len(roster) == 4
    assert {type(p).__name__ for p in roster[2:]} <= {
        "Controller",
        "LowballShedder",
        "Beater",
        "Greedy",
        "RandomBot",
    }


def test_scheduler_mode_for_large_player_counts(test_league):
    game = ThirteenGame(test_league)
    game.players = []
    _add_players(game, 21 + 4)  # > EXHAUSTIVE_MAX_PLAYERS
    state = game._ensure_tournament()
    assert not state["exhaustive"]
    result = game.play_game()
    played = result["table"]["games_played"]
    assert set(played.values()) <= {4, 5}
    assert sum(played.values()) == 4 * 6 * ThirteenGame.SCHEDULER_ROUNDS_PER_CALL


def test_scheduler_round_tables_are_disjoint():
    rng = random.Random(1)
    sched = TableScheduler([f"p{i}" for i in range(14)], rng)
    tables = sched.next_round()
    seated = [p for t in tables for p in t]
    assert len(seated) == len(set(seated)) == 12  # 14 -> 2 byes
    assert all(len(t) == 4 for t in tables)


def test_run_simulations_shape(test_league):
    game = ThirteenGame(test_league)
    game.players = []
    _add_players(game, 4)
    results = game.run_simulations(10, test_league)
    assert set(results.keys()) == {"total_points", "num_simulations", "table"}
    assert results["num_simulations"] == 10
    for key in ("games_won", "avg_finish", "bombs_played"):
        assert set(results["table"][key].keys()) == {p.name for p in game.players}


# --------------------------------------------------------------- feedback


def test_run_single_game_with_feedback_contract(test_league):
    game = ThirteenGame(test_league)
    game.players = []
    _add_players(game, 4)
    out = game.run_single_game_with_feedback()
    fb = out["feedback"]
    assert fb["game"] == "thirteen"
    assert len(fb["players"]) == 4
    assert len(fb["finish_order"]) == len(set(fb["finish_order"])) == 4
    assert fb["winner"] == fb["finish_order"][0]
    assert fb["placements"][fb["winner"]] == 1
    # every card dealt once
    dealt = [c for cards in fb["dealt_hands"].values() for c in cards]
    assert len(dealt) == 52 and len(set(dealt)) == 52
    assert all(len(cs) == 13 for cs in fb["dealt_hands"].values())
    # the holder of the single lowest card opens
    lowest = min(dealt, key=card_key)
    first_play = next(p for p in fb["plays"] if p["action"] == "play")
    assert lowest in fb["dealt_hands"][first_play["seat"]]
    assert first_play["fresh_lead"]


def test_feedback_every_play_is_legal_on_replay(test_league):
    """Replay the recorded play log and verify every move was legal."""
    game = ThirteenGame(test_league)
    game.players = []
    _add_players(game, 4)
    fb = game.run_single_game_with_feedback()["feedback"]
    held = {n: list(cs) for n, cs in fb["dealt_hands"].items()}
    pile = []
    for ev in fb["plays"]:
        seat = ev["seat"]
        if ev["action"] == "pass":
            assert pile, "cannot pass when there is no pile to beat"
        else:
            combo = ev["combo"]
            if ev["fresh_lead"]:
                assert classify(combo) is not None
            else:
                assert beats(combo, pile), f"{seat} played {combo} not beating {pile}"
            for c in combo:
                assert c in held[seat], f"{seat} played {c} it does not hold"
                held[seat].remove(c)
            assert ev["hand_size_after"] == len(held[seat])
            pile = combo
        if ev["cleared"]:
            pile = []
    # everyone but the last finisher emptied their hand
    empty = [n for n, cs in held.items() if not cs]
    assert set(empty) == set(fb["finish_order"][:3])


def test_add_player_with_starter_code(test_league):
    game = ThirteenGame(test_league)
    player = game.add_player(ThirteenGame.starter_code, "TestTeam")
    assert player is not None
    assert len(game.players) == 6  # 5 validation players + the added team
    result = game.play_game()
    assert "TestTeam" in result["points"]
