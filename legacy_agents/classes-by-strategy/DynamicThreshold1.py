from games.greedy_pig.player import Player

class Agent4(Player):
    def make_decision(self, game_state):
        unbanked = game_state['unbanked_money'][self.name]
        banked = game_state['banked_money'][self.name]
        roll_no = game_state['roll_no']
        total_money = banked + unbanked

        # Adjust the threshold for banking based on the current state
        banking_threshold = self.calculate_dynamic_threshold(game_state)

        if unbanked >= banking_threshold or total_money >= 100:
            return "bank"
        return 'continue'

    def calculate_dynamic_threshold(self, game_state):
        # Example of a dynamic threshold calculation
        # This can be adjusted based on more complex strategies
        base_threshold = 23
        round_no = game_state['round_no']

        # Increase threshold in later rounds
        if round_no > 5:
            return base_threshold + 5
        return base_threshold