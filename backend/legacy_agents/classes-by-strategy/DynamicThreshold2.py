from games.greedy_pig.player import Player

class Agent3(Player):
    def calculate_dynamic_threshold(self, game_state):
        # Dynamic threshold calculation similar to Agent 4
        base_threshold = 25
        round_no = game_state['round_no']

        # Increase threshold in later rounds
        if round_no > 5:
            return base_threshold + 5
        return base_threshold

    def make_decision(self, game_state):
        unbanked = game_state['unbanked_money'][self.name]
        banked = game_state['banked_money'][self.name]
        total_money = banked + unbanked

        # Use the dynamic threshold for decision making
        banking_threshold = self.calculate_dynamic_threshold(game_state)

        if unbanked >= banking_threshold or total_money >= 100:
            return "bank"
        return 'continue'