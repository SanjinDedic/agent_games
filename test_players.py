from player_base import Player
import requests
import inspect

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state['unbanked_money'][self.name] >= 20:
            return 'bank'
        return 'continue'

class Dawood_Hassan(Player):
    def make_decision(self, game_state):
        if game_state['unbanked_money'][self.name] >= 10:
            return 'banak'
        return 'continue'
#prints out not valid because the only valid returns are bank or continue on make_decision

class New2_Player(Player):
    def make_decision(self, game_state):
        if game_state['unbanked_money'][self.name] >= 12:
            return 'bank'
        return 'continue'


if __name__ == '__main__':
    ## SENDING A CLASS TO BE RUN
    # code = inspect.getsource(New2_Player)
    # payload={"team_name":"Jen","password":"dMGuJyZt","code":code}
    # response = requests.post("http://localhost:8000/run_single_game/",json=payload)
    # print(response.json()["game_result"])
    
    ## RUNNING SIMULATIONS
    payload={"password":"BOSSMAN","simulations":1,"score":1}
    response = requests.post("http://localhost:8000/run_game_simulation/",json=payload)
    print(response.json()["game_result"])
    