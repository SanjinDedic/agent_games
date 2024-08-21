from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        unbanked = game_state['unbanked_money'][self.name]
        banked = game_state['banked_money'][self.name]
        total_money = banked + unbanked
        if unbanked >= 25 or total_money >= 100:
            return 'bank'
        return 'continue'