"""
Statistical calibration test for the Greedy Pig engine.

Fields 38 fixed-threshold players (bank as soon as unbanked >= N, for
N = 2..39) and drives the real `play_round` for a large number of rounds,
measuring each player's mean banked money per round. This reproduces the
classic "6 sided die - lose score on rolling a 1" chart (mean score per
turn after 1,000,000 turns) using the actual game engine, and compares
every threshold against the exact theoretical expectation computed by
dynamic programming.

Theory note: hold-at-20 and hold-at-21 are *provably identical* — the
continue/bank indifference point is exactly pot = 20 (continue EV is
5/6 * (pot + 4), which equals pot at 20). So the test asserts that
{20, 21} jointly top the table, with {19, 22} completing the top four,
rather than demanding 20 strictly first (that would be a coin flip).
Any real implementation bug — biased die, off-by-one threshold handling,
wrong bust logic, broken banking — shifts the means far outside the
tolerance checked here.

This file lives outside pytest's `testpaths` (backend/tests), so the normal
suite does not pick it up — it is meant to be run explicitly:

    docker compose -f docker-compose.yml -f docker-compose.test.yml \
        run --rm test-runner pytest backend/games/greedy_pig/test_threshold_calibration.py -v -s

The full run is 1,000,000 rounds (~4 minutes). Override the sample size for
a quicker, noisier run (ranking assertions are skipped below 500k rounds):

    ... run --rm -e GREEDY_PIG_CALIBRATION_ROUNDS=50000 test-runner pytest ...
"""

import os
from functools import lru_cache

from backend.database.db_models import League
from backend.games.greedy_pig.greedy_pig import GreedyPigGame
from backend.games.greedy_pig.player import Player

NUM_ROUNDS = int(os.environ.get("GREEDY_PIG_CALIBRATION_ROUNDS", "1000000"))
THRESHOLDS = range(2, 40)  # 38 players


class ThresholdPlayer(Player):
    """Banks as soon as unbanked money reaches the target threshold."""

    def __init__(self, threshold):
        super().__init__()
        self.threshold = threshold
        self.name = f"Bank{threshold:02d}"

    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] >= self.threshold:
            return "bank"
        return "continue"


def exact_expected_banked(threshold):
    """Exact expected banked money per round for a hold-at-threshold player.

    Each roll busts with probability 1/6 (pot lost) or adds 2..6 uniformly;
    the player banks the pot at the first value >= threshold.
    """

    @lru_cache(maxsize=None)
    def value(pot):
        if pot >= threshold:
            return float(pot)
        return sum(value(pot + roll) for roll in range(2, 7)) / 6.0

    return value(0)


def build_game():
    league = League(name="calibration_league", game="greedy_pig")
    game = GreedyPigGame(league)
    game.players = [ThresholdPlayer(t) for t in THRESHOLDS]
    game.scores = {p.name: 0 for p in game.players}
    game.active_players = list(game.players)
    return game


def test_mean_banked_per_round_matches_theory():
    game = build_game()
    gains = {p.name: 0.0 for p in game.players}

    for _ in range(NUM_ROUNDS):
        game.active_players = list(game.players)
        game.play_round()
        for p in game.players:
            gains[p.name] += p.banked_money
            p.banked_money = 0
        game.game_over = False

    means = {name: total / NUM_ROUNDS for name, total in gains.items()}
    ranked = sorted(means.items(), key=lambda kv: kv[1], reverse=True)

    print(f"\nMean banked per round after {NUM_ROUNDS} rounds (top 10):")
    for name, mean in ranked[:10]:
        threshold = int(name[4:])
        print(f"  {name}: {mean:.4f}  (exact: {exact_expected_banked(threshold):.4f})")

    # Every threshold must sit on the exact theoretical curve. Tolerance is
    # ~6 standard errors at 1M rounds and scales for smaller samples.
    tolerance = 0.08 * (1_000_000 / NUM_ROUNDS) ** 0.5
    for t in THRESHOLDS:
        name = f"Bank{t:02d}"
        expected = exact_expected_banked(t)
        assert abs(means[name] - expected) < tolerance, (
            f"{name}: measured {means[name]:.4f}, exact {expected:.4f}, "
            f"tolerance {tolerance:.4f}"
        )

    if NUM_ROUNDS >= 500_000:
        top2 = {name for name, _ in ranked[:2]}
        top4 = {name for name, _ in ranked[:4]}
        assert top2 == {"Bank20", "Bank21"}, (
            f"expected hold-at-20/21 to jointly top the table, got {top2}"
        )
        assert top4 == {"Bank19", "Bank20", "Bank21", "Bank22"}, (
            f"expected top four {{19, 20, 21, 22}}, got {top4}"
        )
