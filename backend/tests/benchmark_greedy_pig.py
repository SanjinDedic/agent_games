"""
Standalone benchmark for the greedy_pig game.

Builds 20 player instances from the seed-script strategies (cycled to reach 20)
and times:
  - 1 game
  - 10 games
  - 100 games   (this is what /simulate sends by default)

Also runs cProfile over 100 games and prints the top hotspots so we can see
where time is actually going.

Run:
  docker compose -f docker-compose.yml -f docker-compose.test.yml \
      run --rm test-runner python -m backend.tests.benchmark_greedy_pig
"""

import cProfile
import io
import pstats
import time
from datetime import timedelta

from backend.database.db_models import League
from backend.games.greedy_pig.greedy_pig import GreedyPigGame
from backend.time_utils import utc_now


STRATEGIES = {
    "alpha_1": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 5:
            return "bank"
        return "continue"
""",
    "alpha_2": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 15:
            return "bank"
        return "continue"
""",
    "alpha_3": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 21:
            return "bank"
        return "continue"
""",
    "alpha_4": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        unbanked = game_state["unbanked_money"][self.name]
        banked = game_state["banked_money"][self.name]
        if banked + unbanked >= 100:
            return "bank"
        if unbanked > 20:
            return "bank"
        return "continue"
""",
    "bravo_1": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["roll_no"] == 3:
            return "bank"
        return "continue"
""",
    "bravo_2": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["roll_no"] == 4:
            return "bank"
        return "continue"
""",
    "bravo_3": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        unbanked = game_state["unbanked_money"][self.name]
        if game_state["roll_no"] >= 4 or unbanked > 18:
            return "bank"
        return "continue"
""",
    "bravo_4": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        unbanked = game_state["unbanked_money"][self.name]
        banked = game_state["banked_money"][self.name]
        rank = self.my_rank(game_state)
        if banked + unbanked >= 100:
            return "bank"
        threshold = 16 if rank == 1 else 24
        if unbanked > threshold:
            return "bank"
        return "continue"
""",
    "charlie_1": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 10:
            return "bank"
        return "continue"
""",
    "charlie_2": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 17:
            return "bank"
        return "continue"
""",
    "charlie_3": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        unbanked = game_state["unbanked_money"][self.name]
        banked = game_state["banked_money"][self.name]
        if banked + unbanked >= 100:
            return "bank"
        if unbanked > 20:
            return "bank"
        return "continue"
""",
    "charlie_4": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        unbanked = game_state["unbanked_money"][self.name]
        banked = game_state["banked_money"][self.name]
        rank = self.my_rank(game_state)
        if banked + unbanked >= 100:
            return "bank"
        leader_banked = max(game_state["banked_money"].values())
        deficit = leader_banked - banked
        threshold = 18
        if rank == 1:
            threshold = 15
        elif deficit > 20:
            threshold = 26
        if unbanked > threshold:
            return "bank"
        return "continue"
""",
    "delta_1": """
from games.greedy_pig.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return random.choice(["bank", "continue"])
""",
    "delta_2": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 12:
            return "bank"
        return "continue"
""",
    "delta_3": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        unbanked = game_state["unbanked_money"][self.name]
        banked = game_state["banked_money"][self.name]
        if banked + unbanked >= 100:
            return "bank"
        if unbanked > 18:
            return "bank"
        return "continue"
""",
    "delta_4": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        unbanked = game_state["unbanked_money"][self.name]
        banked = game_state["banked_money"][self.name]
        rank = self.my_rank(game_state)
        if banked + unbanked >= 100:
            return "bank"
        leader_banked = max(game_state["banked_money"].values())
        deficit = leader_banked - banked
        if rank == 1:
            threshold = 17
        elif deficit > 25:
            threshold = 28
        else:
            threshold = 20
        if game_state["roll_no"] >= 6:
            threshold = min(threshold, 15)
        if unbanked > threshold:
            return "bank"
        return "continue"
""",
}


def build_game_with_20_players():
    """Construct a GreedyPigGame with exactly 20 unique-named players,
    sampled by cycling through the 16 strategies."""
    league = League(
        id=1,
        name="bench_league",
        game="greedy_pig",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=1),
    )
    game = GreedyPigGame(league, verbose=False)
    # Wipe the validation players that BaseGame loaded automatically
    game.players = []
    game.scores = {}

    names = list(STRATEGIES.keys())
    for i in range(20):
        strat_name = names[i % len(names)]
        code = STRATEGIES[strat_name]
        team_name = f"team_{i:02d}_{strat_name}"
        player = game.add_player(code, team_name)
        if player is None:
            raise RuntimeError(f"failed to add player {team_name}")
    return game


def time_run(game, n):
    game.reset()
    t0 = time.perf_counter()
    results = game.run_simulations(num_simulations=n, league=None)
    elapsed = time.perf_counter() - t0
    return elapsed, results


def main():
    print("building game with 20 players...")
    game = build_game_with_20_players()
    print(f"player count: {len(game.players)}")
    print(f"player names: {[p.name for p in game.players]}")

    # Warm up: imports, JIT etc.
    game.reset()
    game.play_game()

    for n in (1, 10, 100):
        elapsed, results = time_run(game, n)
        per_game = elapsed / n
        print(
            f"n={n:>3}: total={elapsed:7.3f}s  "
            f"per-game={per_game*1000:8.2f} ms"
        )

    # cProfile a 100-game run to find hotspots
    print("\n--- cProfile (100 games) top 25 by cumulative time ---")
    game.reset()
    profiler = cProfile.Profile()
    profiler.enable()
    game.run_simulations(num_simulations=100, league=None)
    profiler.disable()

    buf = io.StringIO()
    stats = pstats.Stats(profiler, stream=buf).sort_stats("cumulative")
    stats.print_stats(25)
    print(buf.getvalue())

    print("--- cProfile (100 games) top 25 by total (self) time ---")
    buf = io.StringIO()
    stats = pstats.Stats(profiler, stream=buf).sort_stats("tottime")
    stats.print_stats(25)
    print(buf.getvalue())


if __name__ == "__main__":
    main()
