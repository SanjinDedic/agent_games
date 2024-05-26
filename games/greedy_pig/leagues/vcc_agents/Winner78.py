from games.greedy_pig.player import Player

class CustomPlayer(Player):

    def make_decision(self, game_state):
        import random
        unbank = game_state['unbanked_money'][self.name]
        bank = game_state['banked_money'][self.name]

        if game_state['unbanked_money'][self.name] >= 16  or game_state["roll_no"] == 4 or bank + unbank >= 100:
          return "bank"

        return 'continue'
