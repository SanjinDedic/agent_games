import requests
import inspect

class New5_Player():
    def make_decision(self, game_state):
        import random
        threshold = 1
        #bank if I have won
        if game_state['unbanked_money'][self.name] + game_state['banked_money'][self.name] >= 100:
            return 'bank'
        #continue if I am close to winning
        if game_state['unbanked_money'][self.name] + game_state['banked_money'][self.name] >= 96:
            return 'continue'
        if self.my_rank(game_state) > 5 and game_state['points_aggregate'][self.name] > 80:
            return 'continue'
        if game_state['unbanked_money'][self.name] >= threshold:
            if random.randint(0,10) >1:
                return 'bank' 

        #if I am ranked last then continue
        return 'continue'
    
    

url = 'http://localhost:8000/run_single_game/'

code = inspect.getsource(New5_Player)
data={"team_name":"BoxHill","password":"ighEMkOP","code":code}
response = requests.post(url,json=data)

if response.status_code == 200:
    print(response.json()["game_result"])
else:
    print("An error has occurred.")

#function called when a player banks above a 100
#Correct output for 3 identical scores and 4,5 too