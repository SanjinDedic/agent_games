import requests
import inspect
import time

class Testing_Player():
    def make_decision(self, game_state):
        if len(game_state['players_banked_this_round']) > 2:
            return 'bank'
        return 'continue'


start_t = time.time()



url = 'https://agents.vccfinal.net/submit_agent'
code = inspect.getsource(Testing_Player)
number_of_tests = 50
requests_per_second = 5
success_count = 0
failure_count = 0
responses = dict()


for i in range(number_of_tests):
    data={"team_name":"Sanjin","password":"aaa","code":code}
    response = requests.post(url,json=data)
    if response.status_code not in responses:
        responses[response.status_code] = 1
    else:
        responses[response.status_code] += 1
    sleep_time = round(1/requests_per_second,2)
    time.sleep(sleep_time)

elapse_t = time.time() - start_t
print(f"Elapsed time: {elapse_t}")
print(responses)
