import json
import os

from backend.config import ROOT_DIR


def transform_result(simulation_results, sim_result, league_name):
    return {
        "league_name": league_name,
        "id": sim_result.id if sim_result else None,
        "total_points": simulation_results["total_points"],
        "num_simulations": simulation_results["num_simulations"],
        "timestamp": sim_result.timestamp if sim_result else None,
        "rewards": json.loads(sim_result.custom_rewards) if sim_result else None,
        "table": simulation_results.get("table", {}),
    }


def process_simulation_results(sim, league_name, active=None):
    """
    Process simulation results into a standardized dictionary format.

    Args:
        sim: The SimulationResult object
        league_name: The name of the league
        active: Optional boolean indicating if the league is active

    Returns:
        Dictionary containing formatted simulation results
    """
    total_points = {}
    table_data = {}

    for result in sim.simulation_results:
        team_name = result.team.name
        total_points[team_name] = result.score

        for i in range(1, 4):
            custom_value = getattr(result, f"custom_value{i}")
            custom_value_name = getattr(result, f"custom_value{i}_name")

            if custom_value_name:
                if custom_value_name not in table_data:
                    table_data[custom_value_name] = {}
                table_data[custom_value_name][team_name] = custom_value

    feedback = None
    if sim.feedback_str is not None:
        feedback = sim.feedback_str
    elif sim.feedback_json is not None:
        feedback = json.loads(sim.feedback_json)

    # Build the result dictionary with all possible fields
    result_data = {
        "id": sim.id,
        "league_name": league_name,
        "timestamp": sim.timestamp,
        "total_points": total_points,
        "table": table_data,
        "num_simulations": sim.num_simulations,
        "rewards": (
            json.loads(sim.custom_rewards)
            if isinstance(sim.custom_rewards, str)
            else sim.custom_rewards
        ),
        "feedback": feedback,
        "publish_link": sim.publish_link,  # Include the publish link
    }

    # Add active status if provided
    if active is not None:
        result_data["active"] = active

    return result_data


def get_games_names():
    games_directory = os.path.join(ROOT_DIR, "games")
    if not os.path.exists(games_directory):
        raise FileNotFoundError(f"The directory '{games_directory}' does not exist.")

    # List the contents of the games directory and filter only directories
    game_names = [
        folder
        for folder in os.listdir(games_directory)
        if os.path.isdir(os.path.join(games_directory, folder))
        and folder != "__pycache__"
    ]
    return game_names
