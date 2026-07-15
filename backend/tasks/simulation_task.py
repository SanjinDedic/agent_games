"""Celery task that runs league simulations in a worker process.

The worker holds NO secrets and opens NO database connection: the {team_name:
code} submissions are fetched by the enqueuing API process (which already has a
DB session) and passed in as a task argument. This keeps the process that
executes untrusted agent code credential-free — a breached worker can leak
nothing. Each task still runs in a fresh forked child
(worker_max_tasks_per_child=1) purely for process isolation of agent code.
"""

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from backend.tasks.celery_app import celery_app
from backend.database.db_models import League
from backend.games.game_factory import GameFactory
from backend.time_utils import utc_now

logger = logging.getLogger(__name__)


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
    # Callers wait at most 300s (result.get does not kill the task); without a
    # limit a runaway simulation would occupy the worker forever.
    soft_time_limit=300,
    time_limit=330,
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

    simulation_results = []
    try:
        for _ in range(num_simulations):
            game.reset()
            result = game.play_game(custom_rewards)
            if result is not None:
                simulation_results.append(result)
    except Exception as e:
        logger.error(f"Error running simulations: {str(e)}")
        return {
            "status": "error",
            "message": f"Error running simulations: {str(e)}",
            "simulation_results": {
                "total_points": {},
                "num_simulations": num_simulations,
                "table": {},
            },
        }

    aggregated_results = aggregate_simulation_results(
        simulation_results, num_simulations
    )
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
