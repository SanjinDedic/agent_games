"""Temporary benchmark: find per-game validation simulation counts under 1s.

Mirrors the body of backend/tasks/validation_task.run_validation (feedback game
+ run_simulations + get_player_strategies) using each game's starter_code as
the submitted agent. Run inside the worker image:

docker compose -f docker-compose.yml -f docker-compose.test.yml \
    run --rm --no-deps test-runner python backend/bench_validation.py
"""

import contextlib
import io
import json
import statistics
import time
from datetime import timedelta

from backend.config import GAMES
from backend.database.db_models import League
from backend.games.game_factory import GameFactory
from backend.time_utils import utc_now

# Total validation budget (seconds). Keep headroom below the 1s requirement.
BUDGET = 0.8
FANOUT_GAMES = {"hearts", "ohhell", "thirteen"}  # 1 pass = many sub-games


def make_instance(game_name):
    league = League(
        name="validation_leagueX",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=1),
        game=game_name,
    )
    game_class = GameFactory.get_game_class(game_name)
    instance = game_class(league)
    instance.add_player(game_class.starter_code, "bench_team")
    return instance, league


def timed(fn, *args, **kwargs):
    t0 = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
        io.StringIO()
    ):
        fn(*args, **kwargs)
    return time.perf_counter() - t0


def full_validation(game_name, n_sims):
    """The exact run_validation body, timed like its duration_ms."""
    instance, league = make_instance(game_name)
    t0 = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
        io.StringIO()
    ):
        instance.run_single_game_with_feedback(None)
        instance.reset()
        results = instance.run_simulations(n_sims, league, None)
        results["strategies"] = instance.get_player_strategies()
    return time.perf_counter() - t0, results.get("num_simulations")


def bench_game(game_name):
    instance, league = make_instance(game_name)
    n_players = len(instance.players)

    # Warmup (imports, first-run costs)
    timed(instance.run_single_game_with_feedback, None)
    instance.reset()

    feedback_times = []
    for _ in range(3):
        feedback_times.append(timed(instance.run_single_game_with_feedback, None))
        instance.reset()
    feedback_med = statistics.median(feedback_times)

    # Per-simulation cost: grow N until the batch takes >= 0.2s
    n = 1
    while True:
        elapsed = timed(instance.run_simulations, n, league, None)
        if elapsed >= 0.2 or n >= 512:
            break
        n *= 2
    per_sim = elapsed / n

    max_n = int((BUDGET - feedback_med) / per_sim) if per_sim > 0 else 1
    max_n = max(1, max_n)

    # Round down to a clean number
    for step in (100, 50, 25, 10, 5, 1):
        if max_n >= step:
            rec = (max_n // step) * step
            break
    else:
        rec = 1
    if game_name in FANOUT_GAMES:
        rec = min(rec, max_n)  # keep as computed; typically small already

    # Verify the recommendation end-to-end (3 runs, report max)
    verify = [full_validation(game_name, rec) for _ in range(3)]
    verify_times = [v[0] for v in verify]

    return {
        "game": game_name,
        "players": n_players,
        "feedback_ms": round(feedback_med * 1000, 1),
        "per_sim_ms": round(per_sim * 1000, 2),
        "probe_batch": n,
        "max_n_in_budget": max_n,
        "recommended": rec,
        "verified_total_ms": [round(t * 1000, 1) for t in sorted(verify_times)],
        "reported_num_simulations": verify[0][1],
    }


def main():
    print(f"Games: {GAMES}")
    out = []
    for game_name in GAMES:
        try:
            row = bench_game(game_name)
        except Exception as e:  # noqa: BLE001
            row = {"game": game_name, "error": f"{type(e).__name__}: {e}"}
        print(json.dumps(row))
        out.append(row)
    print("\n=== SUMMARY ===")
    for row in out:
        print(json.dumps(row))


if __name__ == "__main__":
    main()
