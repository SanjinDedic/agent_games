import os
import requests
from sqlmodel import Session, SQLModel, create_engine
from models_db import League, Team, Admin
from auth import get_password_hash
from config import CURRENT_DB, ADMIN_LEAGUE_EXPIRY
from datetime import datetime, timedelta
from database import create_administrator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_URL = "http://localhost:8000"  # Update this if your API is hosted elsewhere
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

def create_admin_and_leagues():
    engine = create_engine(f"sqlite:///{CURRENT_DB}")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        create_administrator(session, 'Administrator', ADMIN_PASSWORD)
        admin_leagues = []
        for i in range(1, 4):
            league_name = f"week{i}"
            league = League(
                name=league_name,
                created_date=datetime.now(),
                expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
                folder=f"leagues/admin/{league_name}",
                game="greedy_pig"
            )
            admin_leagues.append(league)
        session.add_all(admin_leagues)
        session.commit()
        print("Admin and leagues created successfully")

def get_admin_token():
    response = requests.post(f"{API_URL}/admin_login", json={
        "username": "Administrator",
        "password": ADMIN_PASSWORD
    })
    return response.json()["data"]["access_token"]

def create_team(name, password, admin_token):
    response = requests.post(
        f"{API_URL}/team_create",
        json={"name": name, "password": password, "school_name": f"School {name}"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    return response.json()["data"]["access_token"]

def submit_agent(team_token, code):
    response = requests.post(
        f"{API_URL}/submit_agent",
        json={"code": code},
        headers={"Authorization": f"Bearer {team_token}"}
    )
    return response.json()

def assign_to_league(team_token, league_name):
    response = requests.post(
        f"{API_URL}/league_assign",
        json={"name": league_name},
        headers={"Authorization": f"Bearer {team_token}"}
    )
    return response.json()

def create_and_submit_players():
    create_admin_and_leagues()
    admin_token = get_admin_token()

    players = [
        {
            "name": "OptimalPlayer",
            "password": "optimal123",
            "code": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        my_total = game_state["banked_money"][self.name] + game_state["unbanked_money"][self.name]
        leader_total = max(game_state["banked_money"].values())

        if game_state["unbanked_money"][self.name] >= 20 or (my_total >= leader_total and game_state["unbanked_money"][self.name] > 0):
            return 'bank'
        return 'continue'
"""
        },
        {
            "name": "ConservativePlayer",
            "password": "conservative123",
            "code": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] >= 15:
            return 'bank'
        return 'continue'
"""
        },
        {
            "name": "AggressivePlayer",
            "password": "aggressive123",
            "code": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] >= 25:
            return 'bank'
        return 'continue'
"""
        },
        {
            "name": "AdaptivePlayer",
            "password": "adaptive123",
            "code": """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        leader_score = max(game_state["banked_money"].values())
        my_total = game_state["banked_money"][self.name] + game_state["unbanked_money"][self.name]

        if leader_score >= 70:
            if game_state["unbanked_money"][self.name] >= 15:
                return 'bank'
        elif leader_score >= 50:
            if game_state["unbanked_money"][self.name] >= 20:
                return 'bank'
        else:
            if game_state["unbanked_money"][self.name] >= 25:
                return 'bank'

        return 'continue'
"""
        },
        {
            "name": "RandomPlayer",
            "password": "random123",
            "code": """
from games.greedy_pig.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return random.choice(['bank', 'continue'])
"""
        }
    ]

    for player in players:
        print(f"Creating and submitting agent for {player['name']}...")
        team_token = create_team(player['name'], player['password'], admin_token)
        submit_result = submit_agent(team_token, player['code'])
        print(f"Submission result for {player['name']}: {submit_result}")
        assign_result = assign_to_league(team_token, "week1")
        print(f"League assignment result for {player['name']}: {assign_result}")

    print("All players created, submitted, and assigned to week1 successfully")

if __name__ == "__main__":
    create_and_submit_players()