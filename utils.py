# utils.py

import json
from database import create_team

def add_teams_from_json(session, teams_json_path):
    try:
        with open(teams_json_path, 'r') as file:
            data = json.load(file)
            teams_list = data.get('teams', [])  # Use .get to safely handle missing 'teams' key

        for team_data in teams_list:
            # Check if all required fields are present in team_data
            required_fields = ["name", "password"]
            if not all(field in team_data for field in required_fields):
                raise ValueError("Invalid team data in JSON: missing required fields")

            create_result = create_team(session=session, name=team_data["name"], password=team_data["password"], school=team_data.get("school", None))

            # Check for errors in team creation
            if create_result.get("status") == "failed":
                raise ValueError(f"Failed to create team '{team_data['name']}': {create_result['message']}")

    except FileNotFoundError:
        raise FileNotFoundError(f"Error: 'teams_json_path' not found at: {teams_json_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Error: Invalid JSON format in '{teams_json_path}': {str(e)}")
    except (ValueError, KeyError) as e:  # Catch specific errors for better messages
        raise ValueError(f"Error processing team data from JSON: {str(e)}")
    

def transform_result(result_data, sim_id):
    # Sort the total_points dictionary by values
    sorted_total_points = dict(sorted(result_data["total_points"].items(), key=lambda item: item[1], reverse=True))

    # Construct the new dictionary
    return {
        "total_points": sorted_total_points,
        "total_wins": result_data["total_wins"],
        "num_simulations": result_data["num_simulations"],
        "simulation_id": sim_id
    }