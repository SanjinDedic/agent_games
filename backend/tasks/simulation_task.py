"""Celery task that runs league simulations in a worker process.

Replaces the old simulation HTTP service. Submissions are read straight from
the database (the old service round-tripped through the API with a service
token). Each task runs in a fresh forked child (worker_max_tasks_per_child=1),
so the lazily-created DB engine is always born inside the child — no inherited
sockets or stale pools. If max_tasks_per_child is ever removed, dispose the
engine on worker_process_init or switch to NullPool.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlmodel import Session

from backend.tasks.celery_app import celery_app
from backend.database.db_models import League
from backend.database.db_session import get_db_engine
from backend.games.game_factory import GameFactory

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


def _load_league_players(game, league_id: int) -> None:
    """Load the latest league submissions into the game instance.

    Mirrors the old get_all_player_classes_via_api semantics: submissions
    replace the validation players only when there are any; on empty or error
    the validation players loaded by the game constructor stay in place.
    """
    # Deferred import: keeps user_db out of the worker parent (this module is
    # in the Celery include list, so both workers import it at boot) — it is
    # only needed inside the child actually running a simulation.
    from backend.routes.user.user_db import get_latest_submissions_for_league

    try:
        with Session(get_db_engine()) as session:
            submissions = get_latest_submissions_for_league(session, league_id)
    except Exception as e:
        logger.error(f"Error fetching player code: {str(e)}")
        logger.info("Keeping existing validation players due to error")
        return

    if not submissions:
        logger.info("No league submissions found, keeping validation players")
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
    num_simulations: int = 100,
    custom_rewards: Optional[List[int]] = None,
    player_feedback: bool = False,
) -> Dict[str, Any]:
    """Run simulations and return {status, feedback, player_feedback, simulation_results}."""
    league = League(
        id=league_id,
        name="simulation_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=1),
        game=game_name,
    )

    game_class = GameFactory.get_game_class(game_name)
    game = game_class(league)

    _load_league_players(game, league_id)

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
