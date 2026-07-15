"""Celery task that runs league simulations in a worker process.

The worker holds NO secrets and opens NO database connection: the {team_name:
code} submissions are fetched by the enqueuing API process (which already has a
DB session) and passed in as a task argument. This keeps the process that
executes untrusted agent code credential-free — a breached worker can leak
nothing. Each task still runs in a fresh forked child
(worker_max_tasks_per_child=1) purely for process isolation of agent code.
"""

import logging
import os
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional

from celery.exceptions import SoftTimeLimitExceeded

from backend.tasks.celery_app import celery_app
from backend.database.db_models import League
from backend.games.game_factory import GameFactory
from backend.time_utils import utc_now

logger = logging.getLogger(__name__)

# 10-minute hard ceiling. Celery kills the task at the soft limit; the loop
# below stops launching new games at SIMULATION_TIME_BUDGET_SECONDS, which sits
# safely under it, so the task returns on a whole-simulation boundary well
# before Celery would ever interrupt a game mid-play. (Interrupting mid-game
# would drop a partial result and bias the scores toward whoever was ahead.)
SIMULATION_SOFT_TIME_LIMIT = int(os.environ.get("SIMULATION_TIMEOUT_SECONDS", "600"))
SIMULATION_HARD_TIME_LIMIT = SIMULATION_SOFT_TIME_LIMIT + 30

# The loop stops starting new games once the elapsed time plus the running
# average per-game cost would cross this. The 30s gap below the soft limit
# leaves room for the game already in flight to finish plus final aggregation.
SIMULATION_TIME_BUDGET_SECONDS = int(
    os.environ.get("SIMULATION_BUDGET_SECONDS", str(SIMULATION_SOFT_TIME_LIMIT - 30))
)


def aggregate_simulation_results(simulation_results, num_simulations):
    """Aggregate results from multiple simulations"""
    total_points = {}
    table_data = {}

    # Initialize counters for each player
    for result in simulation_results:
        if result and "points" in result:
            for player in result["points"]:
                if player not in total_points:
                    total_points[player] = 0

    # Sum points
    for result in simulation_results:
        if result and "points" in result:
            for player, points in result["points"].items():
                total_points[player] += points

    # Get table data from last successful simulation
    if simulation_results and "table" in simulation_results[-1]:
        table_data = simulation_results[-1]["table"]

    return {
        "total_points": total_points,
        "num_simulations": num_simulations,
        "table": table_data,
    }


def _load_submitted_players(game, submissions: Optional[Dict[str, str]]) -> None:
    """Load the league's submitted agents into the game instance.

    `submissions` is a {team_name: code} map fetched by the enqueuing API
    process and passed in as a task arg — the worker never touches the DB.
    Mirrors the old get_all_player_classes_via_api semantics: submissions
    replace the validation players only when there are any; on an empty/None
    map the validation players loaded by the game constructor stay in place. A
    submission whose code fails to construct a player is skipped, not fatal.
    """
    if not submissions:
        logger.info("No league submissions provided, keeping validation players")
        return

    game.players = []
    game.scores = {}
    for team_name, code in submissions.items():
        try:
            game.add_player(code, team_name)
        except Exception as e:
            logger.error(f"Error creating player {team_name}: {str(e)}")
    logger.info(f"Total league players loaded: {len(game.players)}")


@celery_app.task(
    name="simulation.run",
    # 10-minute ceiling. The task's own budget (SIMULATION_TIME_BUDGET_SECONDS)
    # stops it cleanly before this fires; the soft limit is only a backstop for
    # a single pathologically slow game, and even then SoftTimeLimitExceeded is
    # caught below so completed simulations are still returned.
    soft_time_limit=SIMULATION_SOFT_TIME_LIMIT,
    time_limit=SIMULATION_HARD_TIME_LIMIT,
)
def run_simulation(
    league_id: int,
    game_name: str,
    submissions: Optional[Dict[str, str]] = None,
    num_simulations: int = 100,
    custom_rewards: Optional[List[int]] = None,
    player_feedback: bool = False,
) -> Dict[str, Any]:
    """Run simulations and return {status, feedback, player_feedback, simulation_results}.

    `submissions` is the {team_name: code} map fetched by the API before enqueue;
    when empty the game's built-in validation players are used instead.
    """
    # Anchor the 10-minute budget at task entry so the feedback game, player
    # loading and everything else count against it — not just the loop.
    task_start = time.perf_counter()

    league = League(
        id=league_id,
        name="simulation_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=1),
        game=game_name,
    )

    game_class = GameFactory.get_game_class(game_name)
    game = game_class(league)

    _load_submitted_players(game, submissions)

    if not game.players:
        return {
            "status": "error",
            "message": "No players loaded for simulation",
            "simulation_results": {
                "total_points": {},
                "num_simulations": num_simulations,
                "table": {},
            },
        }

    feedback_result = {
        "feedback": "No feedback",
        "player_feedback": "No player feedback",
    }

    if player_feedback:
        try:
            feedback_result = game.run_single_game_with_feedback(custom_rewards)
        except Exception as e:
            logger.error(f"Error running feedback game: {str(e)}")
            return {
                "status": "error",
                "message": f"Error running feedback game: {str(e)}",
                "simulation_results": {
                    "total_points": {},
                    "num_simulations": num_simulations,
                    "table": {},
                },
            }

    # --- Time-bounded simulation loop -------------------------------------
    # A user can ask for up to 10000 runs; for a game whose single play_game
    # takes seconds that is hours of work. Instead of letting the request run
    # unbounded (only for Celery to kill it and return nothing), we run games
    # one at a time and stop launching new ones once the elapsed time plus the
    # running-average cost of a game would cross SIMULATION_TIME_BUDGET_SECONDS.
    #
    # The guard is checked BEFORE each game starts and never interrupts one in
    # progress, so every result in the batch is a whole game — the aggregate is
    # never skewed by a partial game that stopped with someone mid-lead. The
    # budget sits below the Celery soft limit so that limit effectively never
    # fires; SoftTimeLimitExceeded is still caught as a backstop and returns the
    # completed games rather than discarding them.
    requested_simulations = num_simulations
    simulation_results = []
    runs_attempted = 0
    budget_reached = False
    try:
        sim_start = time.perf_counter()

        for _ in range(num_simulations):
            now = time.perf_counter()
            total_elapsed = now - task_start
            # After the first game we know its real cost; project whether the
            # next one fits before starting it (never mid-game). The average is
            # over simulation games only; total_elapsed is the whole-task clock.
            if runs_attempted:
                avg_per_game = (now - sim_start) / runs_attempted
                if total_elapsed + avg_per_game >= SIMULATION_TIME_BUDGET_SECONDS:
                    budget_reached = True
                    logger.warning(
                        "Simulation budget (%ds) reached for league %s (%s): "
                        "ran %d of %d requested (avg %.3fs/game)",
                        SIMULATION_TIME_BUDGET_SECONDS, league_id, game_name,
                        runs_attempted, requested_simulations, avg_per_game,
                    )
                    break

            game.reset()
            result = game.play_game(custom_rewards)
            runs_attempted += 1
            if result is not None:
                simulation_results.append(result)
    except SoftTimeLimitExceeded:
        # Backstop only: the budget above should have stopped us first. A game
        # in progress when this fires was never appended, so simulation_results
        # still holds only whole games — return them instead of the whole batch.
        budget_reached = True
        logger.warning(
            "Soft time limit hit for league %s after %d completed simulations; "
            "returning partial results",
            league_id, runs_attempted,
        )
    except Exception as e:
        logger.error(f"Error running simulations: {str(e)}")
        return {
            "status": "error",
            "message": f"Error running simulations: {str(e)}",
            "simulation_results": {
                "total_points": {},
                "num_simulations": requested_simulations,
                "table": {},
            },
        }

    aggregated_results = aggregate_simulation_results(
        simulation_results, runs_attempted
    )
    aggregated_results["requested_simulations"] = requested_simulations
    aggregated_results["capped"] = budget_reached
    # Only validation players declare a strategy, so this is empty whenever
    # real league submissions replaced them.
    aggregated_results["strategies"] = game.get_player_strategies()

    return {
        "status": "success",
        "feedback": feedback_result["feedback"],
        "player_feedback": (
            feedback_result["player_feedback"]
            if player_feedback
            else "No player feedback"
        ),
        "simulation_results": aggregated_results,
    }
