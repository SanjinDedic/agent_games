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
