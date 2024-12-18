import json
import uuid

from locust import HttpUser, between, task


class CustomPlayer:

    def make_decision(self, game_state):
        import random

        # Change this algorithm. You must return 'bank' or 'continue'.
        # bankchance = random.randint(1,2)
        if game_state["unbanked_money"][self.name] >= random.randint(5, 20):
            # if bankchance == 1:
            return "bank"

        return "continue"


class UserBehavior(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        self.team_list = self.load_teams()
        self.headers = {"X-Forwarded-For": str(uuid.uuid4())}

    def load_teams(self):
        with open("teams.json", "r") as file:
            list_data = json.load(file)
            return list_data["teams"]

    @task
    def get_root(self):
        self.client.get("/")
