from player_base import Player

class Testing_Player(Player):
    def make_decision(self, game_state):
        threshold = 12
        #print("Sanjin Game State:", game_state)
        if game_state['unbanked_money'][self.name] + game_state['banked_money'][self.name] >= 100:
            return 'bank'
        if game_state['unbanked_money'][self.name] + game_state['banked_money'][self.name] >= 96:
            return 'continue'
        if game_state['unbanked_money'][self.name] >= threshold:
            return 'bank'
        #if I am ranked last then continue


        return 'continue'
