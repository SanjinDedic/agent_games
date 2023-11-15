import requests
import inspect

class New4_Player():
    def make_decision(self, game_state):
        if game_state['unbanked_money'][self.name] >= 12:
            return 'bank'
        return 'continue'
    
    

url = 'http://localhost:8000/run_single_game/'

code = inspect.getsource(New4_Player)
data={"team_name":"BoxHill","password":"ighEMkOP","code":code}
response = requests.post(url,json=data)

if response.status_code == 200:
    print(response.json()["game_result"])
else:
    print("An error has occurred.")