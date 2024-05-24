from player import Player

class Agent1(Player):
    def make_decision(self, game_state):
        unbanked = game_state['unbanked_money'][self.name]
        banked = game_state['banked_money'][self.name]
        roll_no = game_state['roll_no']
        total_money = banked + unbanked
        if unbanked >= 16  or roll_no == 4 or total_money >= 100:
          return "bank"

        return 'continue'