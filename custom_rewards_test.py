import os
import sys
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

# Add the project root directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from api import app
from config import ROOT_DIR

# Connect to local copy of prod database
db_path = os.path.join(ROOT_DIR, "teams.db")
engine = create_engine(f"sqlite:///{db_path}")

def get_db_session():
    with Session(engine) as session:
        yield session

app.dependency_overrides[get_db_session] = get_db_session

client = TestClient(app)

def get_admin_token():
    response = client.post("/admin_login", json={"username": "Administrator", "password": "BOSSMAN"})
    return response.json()["data"]["access_token"]

def run_simulation(league_name, num_simulations, custom_rewards, token):
    response = client.post(
        "/run_simulation",
        json={"league_name": league_name, "num_simulations": num_simulations, "custom_rewards": custom_rewards},
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()

def test_custom_rewards():
    admin_token = get_admin_token()
    league_name = "week1"
    num_simulations = 1000

    # Test with default rewards
    default_result = run_simulation(league_name, num_simulations, None, admin_token)
    print("Default Rewards Result:")
    print(default_result)

    # Test with custom rewards
    custom_rewards = [1, 5, 8, 10]
    custom_result = run_simulation(league_name, num_simulations, custom_rewards, admin_token)
    print("\nCustom Rewards Result:")
    print(custom_result)

    # Compare results
    print("\nComparison:")
    default_points = default_result["data"]["total_points"]
    custom_points = custom_result["data"]["total_points"]

    for player in default_points.keys():
        default_score = default_points[player]
        custom_score = custom_points[player]
        difference = custom_score - default_score
        print(f"{player}: Default: {default_score}, Custom: {custom_score}, Difference: {difference}")

if __name__ == "__main__":
    test_custom_rewards()