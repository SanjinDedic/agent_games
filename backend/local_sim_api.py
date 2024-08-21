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
# If you have errors run python3 production_database_setup.py
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

def run_simulation(league_name, num_simulations, token):
    response = client.post(
        "/run_simulation",
        json={"league_name": league_name, "num_simulations": num_simulations},
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()

if __name__ == "__main__":
    admin_token = get_admin_token()
    league_name = "week1"
    num_simulations = 1000

    result = run_simulation(league_name, num_simulations, admin_token)
    print(result)