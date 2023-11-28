import requests
import inspect
import time


class Testing_Player():
    def make_decision(self, game_state):
        if len(game_state['players_banked_this_round']) > 2:
            return 'bank'
        return 'continue'
        
start_t = time.time()
url = 'agents.vccfinal:8000/submit_agent/'

code = inspect.getsource(Testing_Player)
data={"team_name":"Sanjin","password":"aaa","code":code}
response = requests.post(url,json=data)

if response.status_code == 200:
    print(response.json())
else:
    print("An error has occurred.")

elapse_t = time.time() - start_t
print("Time elapsed: ", elapse_t)