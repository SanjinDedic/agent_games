import json
import random
import threading
import time
from itertools import cycle
from locust import HttpUser, task, between
from locust.exception import StopUser
from requests.exceptions import ConnectionError

with open('teams.json', 'r') as f:
    teams_data = json.load(f)
    teams_list = teams_data['teams']

random.shuffle(teams_list)
teams_iterator = cycle(teams_list)
iterator_lock = threading.Lock()

class AgentUser(HttpUser):
    
    wait_time = between(4, 8)

    def on_start(self):
        with iterator_lock:
            self.team = next(teams_iterator)
        self.submissions_made = 0

        if not self.login():
            raise StopUser()
        if not self.assign_to_league():
            raise StopUser()

    def login(self):
        try:
            response = self.client.post("/team_login", json={
                "name": self.team['name'],
                "password": self.team['password']
            })
            if response.status_code == 200:
                self.access_token = response.json()['data']['access_token']
                self.client.headers.update({
                    "Authorization": f"Bearer {self.access_token}"
                })
                return True
            else:
                print(f"Login failed for team {self.team['name']}")
                return False
        except Exception as e:
            print(f"Exception during login for team {self.team['name']}: {e}")
            return False

    def assign_to_league(self):
        try:
            league_data = {
                "name": "prison"
            }
            response = self.client.post("/league_assign", json=league_data)
            if response.status_code == 200:
                print(f"Team {self.team['name']} assigned to league 'prison' successfully.")
                return True
            else:
                print(f"Failed to assign team {self.team['name']} to league. Response: {response.text}")
                return False
        except Exception as e:
            print(f"Exception during league assignment for team {self.team['name']}: {e}")
            return False

    def generate_agent_code(self):
        # Example agent code with slight modifications
        code_template = '''
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        opponent_history = game_state['opponent_history']
        if not opponent_history:
            return '{first_move}'
        if opponent_history[-1] == '{opponent_last_move}':
            return '{response_move}'
        return '{default_move}'
'''
        # Randomize moves
        moves = ['collude', 'defect']
        code = code_template.format(
            first_move=random.choice(moves),
            opponent_last_move=random.choice(moves),
            response_move=random.choice(moves),
            default_move=random.choice(moves)
        )
        return code

    @task
    def submit_agent_code(self):
        if self.submissions_made >= 10:
            raise StopUser()  # Stop this user after 5 submissions

        code = self.generate_agent_code()

        submission_data = {
            "code": code
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.post("/submit_agent", json=submission_data)
                if response.status_code == 200:
                    print(f"Team {self.team['name']} submitted agent code successfully.")
                    self.submissions_made += 1
                    break
                else:
                    print(f"Team {self.team['name']} failed to submit agent code.")
                    print(f"Response: {response.text}")
                    break
            except ConnectionError as e:
                print(f"ConnectionError on attempt {attempt+1} for team {self.team['name']}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Wait before retrying
                    continue
                else:
                    print(f"Failed to submit after {max_retries} attempts.")
            except Exception as e:
                print(f"Exception while submitting agent code: {e}")
                break