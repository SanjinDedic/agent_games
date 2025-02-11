import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import requests

# Configuration
API_BASE_URL = "http://localhost:8000"  # Update with your API URL
API_KEY = "FDSWUqv0k1ljbkgyV6bSoz0Y9YC2bytNGiYtpteRWvw"
RESULTS_FILE = "simulation_results.json"

# Sample Connect4 agent code
CONNECT4_AGENT_CODE = """
from games.connect4.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        # Simple strategy: choose random valid move
        move = random.choice(game_state["possible_moves"])
        
        # Add custom feedback for monitoring
        self.add_feedback(f"Selected move: {move}")
        
        return move
"""


class SimulationRequest:
    def __init__(
        self,
        league_id: int,
        game_name: str,
        num_simulations: int = 100,
        custom_rewards: Optional[List[int]] = None,
        player_feedback: bool = False,
    ):
        self.league_id = league_id
        self.game_name = game_name
        self.num_simulations = num_simulations
        self.custom_rewards = custom_rewards
        self.player_feedback = player_feedback

    def to_dict(self) -> dict:
        return {
            "league_id": self.league_id,
            "game_name": self.game_name,
            "num_simulations": self.num_simulations,
            "custom_rewards": self.custom_rewards,
            "player_feedback": self.player_feedback,
        }


class ResultsManager:
    def __init__(self, filename: str):
        self.filename = filename
        self.ensure_file_exists()

    def ensure_file_exists(self):
        if not os.path.exists(self.filename):
            with open(self.filename, "w") as f:
                json.dump({"results": []}, f, indent=2)

    def get_next_id(self) -> int:
        try:
            with open(self.filename, "r") as f:
                data = json.load(f)
                if not data["results"]:
                    return 1
                return max(result["id"] for result in data["results"]) + 1
        except Exception as e:
            print(f"Error getting next ID: {e}")
            return 1

    def add_result(self, result: dict):
        try:
            with open(self.filename, "r") as f:
                data = json.load(f)

            # Add metadata to result
            result["id"] = self.get_next_id()
            result["timestamp"] = datetime.now().isoformat()

            data["results"].append(result)

            with open(self.filename, "w") as f:
                json.dump(data, f, indent=2)

            print(f"Result saved with ID: {result['id']}")
        except Exception as e:
            print(f"Error saving result: {e}")


class AgentAPI:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.token = None
        self.team_name = "test_agent"  # Default team name
        self.league_id = 4  # Agent league ID from production_database_setup.py
        self.results_manager = ResultsManager(RESULTS_FILE)

    def authenticate(self) -> bool:
        """Authenticate with the API and get a token"""
        try:
            print("Authenticating...")
            response = requests.post(
                f"{self.base_url}/auth/agent-login", json={"api_key": self.api_key}
            )

            data = response.json()
            if data["status"] == "success":
                self.token = data["data"]["access_token"]
                print("Authentication successful")
                return True
            else:
                print(f"Authentication failed: {data['message']}")
                return False

        except Exception as e:
            print(f"Authentication error: {e}")
            return False

    def get_headers(self) -> Dict:
        """Get headers with authentication token"""
        return {"Authorization": f"Bearer {self.token}"}

    # backend/agent_script.py
    # Update the validate_agent method in AgentAPI class
    def validate_agent(self, code: str, game_name: str, team_name: str) -> Dict:
        """Submit agent code for validation and storage"""
        try:
            print(f"Submitting {team_name}'s {game_name} agent...")
            response = requests.post(
                f"{self.base_url}/user/submit-agent",
                headers=self.get_headers(),
                json={"code": code},
            )
            return response.json()
        except Exception as e:
            print(f"Submission error: {e}")
            return None

    def run_simulation(
        self,
        code: str,
        game_name: str,
        num_simulations: int = 100,
        custom_rewards: Optional[List[int]] = None,
    ) -> Dict:
        """Run a simulation with the agent"""
        try:
            sim_request = SimulationRequest(
                league_id=self.league_id,
                game_name=game_name,
                num_simulations=num_simulations,
                custom_rewards=custom_rewards,
                player_feedback=False,
            )

            print(f"Running {num_simulations} simulations...")
            response = requests.post(
                f"{self.base_url}/agent/simulate",
                headers=self.get_headers(),
                json=sim_request.to_dict(),
            )

            result = response.json()

            # Save the simulation result
            if result["status"] == "success":
                self.results_manager.add_result(
                    {
                        "team_name": self.team_name,
                        "game_name": game_name,
                        "num_simulations": num_simulations,
                        "custom_rewards": custom_rewards,
                        "results": result["data"] if "data" in result else None,
                    }
                )

            return result

        except Exception as e:
            print(f"Simulation error: {e}")
            return None


def main():
    # Initialize API client
    api = AgentAPI(API_BASE_URL, API_KEY)

    # Step 1: Authenticate
    if not api.authenticate():
        return

    # Step 2: Validate agent
    validation_result = api.validate_agent(
        code=CONNECT4_AGENT_CODE, game_name="connect4", team_name=api.team_name
    )

    if validation_result:
        print("\nValidation Response: uncommend line 205")
        # print(validation_result)

    # Step 3: Run simulation
    if validation_result and validation_result["status"] == "success":
        simulation_result = api.run_simulation(
            code=CONNECT4_AGENT_CODE,
            game_name="connect4",
            num_simulations=10,  # Reduced for testing
        )

        if simulation_result:
            print("\nSimulation Results:")
            print(f"Status: {simulation_result['status']}")
            print(f"Message: {simulation_result['message']}")
            if simulation_result.get("data"):
                results = simulation_result["data"]
                print("\nPoints Distribution:")
                for player, points in results.get("total_points", {}).items():
                    print(f"{player}: {points} points")
                print(f"\nTotal Simulations Run: {results.get('num_simulations')}")
                if "table" in results:
                    print("\nDetailed Statistics:")
                    print(results["table"])


if __name__ == "__main__":
    main()
