import random
import os
import time
from player_base import Player
import importlib.util

class Dice:
    def roll(self):
        return random.randint(1, 6)

class Game:
    def __init__(self, player_classes):
        # Create player instances from the provided classes
        self.players = [PlayerClass(f"{filename[:-3]}", "abc123") for PlayerClass, filename in player_classes]
        self.active_players = list(self.players)
        self.dice = Dice()
        self.players_banked_this_round = set()

    def get_game_state(self):
        return {
            "banked_money": {player.name: player.banked_money for player in self.players},
            "unbanked_money": {player.name: player.unbanked_money for player in self.players},
            "points_aggregate": {player.name: player.banked_money + player.unbanked_money for player in self.players}
        }
    
    def play_round(self):
        for player in self.active_players:
            player.reset_turn()  # Resetting the banking status at the start of each turn

        while True:
            roll = self.dice.roll()
            if roll == 1:
                for player in self.active_players:
                    player.reset_unbanked_money()
                break  # End of the turn

            for player in self.active_players:
                player.unbanked_money += roll
                decision = player.make_decision(self.get_game_state())
                if decision == 'bank' and not player.has_banked_this_turn:
                    player.bank_money()
                    player.has_banked_this_turn = True

    def play_game(self):
        while max(player.banked_money for player in self.players) < 100:
            self.active_players = list(self.players)  # reset active players for the round
            self.play_round()
        winner = max(self.players, key=lambda player: player.banked_money)
        game_state = self.get_game_state()
        return game_state

    def print_rankings(self, file):
        file.write("\n\n")
        file.write("-" * 20)
        file.write("\nFinal Rankings and Points:\n")
        ranked_players = sorted(self.players, key=lambda player: player.banked_money, reverse=True)

        # Initial points based on ranking (5 for 1st, 4 for 2nd, and so on)
        points_dict = {player.name: 5 - i for i, player in enumerate(ranked_players)}

        # Adjust points for ties
        for i in range(len(ranked_players) - 1):
            if ranked_players[i].banked_money == ranked_players[i + 1].banked_money:
                tied_point = max(1, points_dict[ranked_players[i + 1].name])
                points_dict[ranked_players[i].name] = tied_point

        # Write the final points to the file
        for i, player in enumerate(ranked_players, start=1):
            player_name = player.name
            player_points = points_dict[player_name]
            file.write(f"{i}. {player_name} with {player.banked_money} banked, {player_points} points\n")

        file.write("-" * 20)
        file.write("\n\n\n")


def run_simulation_many_times(number):
    
    all_players = get_all_player_classes_from_folder()
    if not all_players:
        raise ValueError("No player classes provided.")

    # Dictionary to store the total points for each player
    total_points = {filename[:-3]: 0 for _, filename in all_players}

    current_time = time.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"logfiles/game_simulation_{number}_runs_{current_time}.txt"
    
    for _ in range(number):
        game = Game(all_players)
        game_result = game.play_game()
        points_this_game = assign_points(game_result)

        # Update total_points with the points from this game
        for player, points in points_this_game.items():
            total_points[player] += points

    # Print the results
    results = [f"{number} games were played"]
    for player_name in sorted(total_points, key=total_points.get, reverse=True):
        results.append(f"{player_name} earned a total of {total_points[player_name]} points")

    with open(filename, 'w') as file:
        file.write("\n".join(results))

    return "\n".join(results)

def run_animation(refresh_rate, number):
    all_players = get_all_player_classes_from_folder()
    if not all_players:
        raise ValueError("No player classes provided.")

    # Dictionary to store the total points for each player
    total_points = {filename[:-3]: 0 for _, filename in all_players}

    current_time = time.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"logfiles/game_simulation_{number}_runs_{current_time}.txt"
    
    with open(filename, 'w') as file:
        for i in range(number):
            game = Game(all_players)
            game_result = game.play_game(file)
            points_this_game = assign_points(game_result)

            # Update total_points with the points from this game
            for player, points in points_this_game.items():
                total_points[player] += points  
            if i % refresh_rate == 0:
                os.system('clear')
                results = [f"{i} games were played"]
                for player_name in sorted(total_points, key=total_points.get, reverse=True):
                    results.append(f"{player_name} earned a total of {total_points[player_name]} points")
                print("\n".join(results))
                time.sleep(1)
    print("\n".join(results))

def get_all_player_classes_from_folder(folder_name="classes"):
    # Get a list of all .py files in the given folder
    files = [f for f in os.listdir(folder_name) if os.path.isfile(os.path.join(folder_name, f)) and f.endswith('.py')]

    player_classes = []

    for file in files:
        module_name = file[:-3]  # remove the ".py" extension
        spec = importlib.util.spec_from_file_location(module_name, os.path.join(folder_name, file))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Check each item in the module to see if it's a subclass of Player
        for name, obj in vars(module).items():
            if isinstance(obj, type) and issubclass(obj, Player) and obj is not Player:
                player_classes.append((obj, file))
    return player_classes


def assign_points(game_result):
    banked_money = game_result['banked_money']
    
    sorted_scores = sorted(banked_money.items(), key=lambda x: x[1], reverse=True)
    max_score = 21
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

    # Adjust points for ties
    score_counts = {score: sum(player_score == score for player_score in banked_money.values())
                    for score in set(banked_money.values())}

    for player, score in banked_money.items():
        if score_counts[score] > 1 and points_distribution.get(player, 0) > 0:
            points_distribution[player] -= 1
    
    return points_distribution


if __name__ == "__main__":
    print(run_simulation_many_times(1000))