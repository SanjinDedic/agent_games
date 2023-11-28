import random
from abc import ABC, abstractmethod

class Player(ABC):
    def __init__(self, name, password):
        self.name = name
        self.password = password
        self.banked_money = 0
        self.unbanked_money = 0
        self.has_banked_this_turn = False  # Track banking status within a turn

    def reset_unbanked_money(self):
        self.unbanked_money = 0

    def bank_money(self):
        self.banked_money += self.unbanked_money
        self.reset_unbanked_money()

    def reset_turn(self):
        self.has_banked_this_turn = False  # Reset banking status at the start of each turn

    @abstractmethod
    def make_decision(self, game_state):
        pass


class Dice:
    def roll(self):
        return random.randint(1, 6)

class Game:
    def __init__(self, player_classes):
        # Create player instances from the provided classes
        self.players = get_all_player_classes_from_folder()
        self.active_players = list(self.players)
        self.dice = Dice()
        self.players_banked_this_round = []
        self.round_no = 0
        self.roll_no = 0

    def get_game_state(self):
        return {
            "round_no": self.round_no,
            "roll_no": self.roll_no,
            "players_banked_this_round": self.players_banked_this_round,
            "banked_money": {player.name: player.banked_money for player in self.players},
            "unbanked_money": {player.name: player.unbanked_money for player in self.players},
        }
    
    def play_round(self):
        self.players_banked_this_round = []
        self.round_no += 1
        self.roll_no = 0
        for player in self.active_players:
            player.reset_turn()  # Resetting the banking status at the start of each turn

        while True:
            self.roll_no += 1
            roll = self.dice.roll()
            # If roll is 1, all players lose unbanked money and the round ends
            if roll == 1:
                for player in self.active_players:
                    player.reset_unbanked_money()
                    #print('---------TURN END----------')
                break

            # Process each player's turn
            for player in self.active_players:
                if not player.has_banked_this_turn:
                    player.unbanked_money += roll
                    decision = player.make_decision(self.get_game_state())
                    if decision == 'bank':
                        player.bank_money()
                        player.has_banked_this_turn = True
                        self.players_banked_this_round.append(player.name)
                        # Check if the player has won after banking
                        if player.banked_money >= 100:
                            return  # End the round if a player has won

            # Check if all players have banked, then end the round
            if all(player.has_banked_this_turn for player in self.active_players):
                break

    def play_game(self):
        while max(player.banked_money for player in self.players) < 100:
            self.active_players = list(self.players)  # reset active players for the round
            self.play_round()
        game_state = self.get_game_state()
        return game_state


def run_simulation_many_times(number):
    all_players = get_all_player_classes_from_folder()
    if not all_players:
        raise ValueError("No player classes provided.")

    # Dictionary to store the total points for each player
    total_points = {player.name: 0 for player in all_players}

    for _ in range(number):
        game = Game(all_players)
        game_result = game.play_game()
        points_this_game = assign_points(game_result)
        for player, points in points_this_game.items():
            total_points[player] += points

    # Print the results
    results = [f"{number} games were played"]
    for player_name in sorted(total_points, key=total_points.get, reverse=True):
        results.append(f"{player_name} earned a total of {total_points[player_name]} points")
    return "\n".join(results)


def assign_points(game_result, max_score=6):
    banked_money = game_result['banked_money']
    
    sorted_scores = sorted(banked_money.items(), key=lambda x: x[1], reverse=True)
    points_distribution = {}
    last_score = None
    last_rank = 0

    for rank, (player, score) in enumerate(sorted_scores, start=1):
        if score != last_score:  # New score, update rank
            last_rank = rank
        last_score = score

        # Assign points based on rank
        points = max(max_score - last_rank, 0)
        points_distribution[player] = points
  
    return points_distribution


class Agent1(Player):
    def __init__(self):
        super().__init__("Agent1", "password")
    def make_decision(self, game_state):
        unbanked = game_state['unbanked_money'][self.name]
        banked = game_state['banked_money'][self.name]
        roll_no = game_state['roll_no']
        total_money = banked + unbanked
        if unbanked >= 16  or roll_no == 4 or total_money >= 100:
          return "bank"

        return 'continue'

class Agent2(Player):
    def __init__(self):
        super().__init__("Agent2", "password")
    def make_decision(self, game_state):
        # Change this algorithm. You must return 'bank' or 'continue'.
        if game_state['unbanked_money'][self.name] >= 17:
            return 'bank'

        return 'continue'

class Agent3(Player):
    def __init__(self):
        super().__init__("Agent3", "password")

    def calculate_dynamic_threshold(self, game_state):
        # Dynamic threshold calculation similar to Agent 4
        base_threshold = 15
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


class Agent4(Player):
    def __init__(self):
        super().__init__("Agent4", "password")

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
        base_threshold = 15
        round_no = game_state['round_no']

        # Increase threshold in later rounds
        if round_no > 5:
            return base_threshold + 5
        return base_threshold
    

class Agent5(Player):
    def __init__(self):
        super().__init__("Agent5", "password")

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



def get_all_player_classes_from_folder(folder_name="classes"):
    return [Agent1(), Agent2(), Agent3(), Agent4(), Agent5()]
    


if __name__ == "__main__":
    print(run_simulation_many_times(1000))