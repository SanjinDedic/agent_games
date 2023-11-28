from player_base import Player

class Agent5(Player):
    def make_decision(self, game_state):
        import random
        unbanked = game_state['unbanked_money'][self.name]
        banked = game_state['banked_money'][self.name]
        total_money = banked + unbanked

        # Adjust the threshold for banking based on the current state
        threshold = random.randint(20,24)

        if unbanked >= threshold or total_money >= 100:
            return "bank"
        return 'continue'