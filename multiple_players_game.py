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

    def get_game_state(self):
        return {
            "banked_money": {player.name: player.banked_money for player in self.players},
            "unbanked_money": {player.name: player.unbanked_money for player in self.players}
        }
    
    def play_round(self,file):
        game_state= self.get_game_state()
        roll = self.dice.roll()
        if roll == 1:
            file.write('Gamemaster rolled a 1. Round over without banking money.\n')
            for player in self.active_players:
                player.reset_unbanked_money()
            return
    
        for player in self.active_players:

            player.unbanked_money += roll
            decision = player.make_decision(game_state)
            if decision == 'bank':
                player.bank_money()
                file.write(f'{player.name} decided to bank. They now have {player.banked_money} in bank.\n')
            else:
                file.write(f'{player.name} decided to not to bank. They now have {player.banked_money} in bank.\n')


    def play_game(self,file):
        while max(player.banked_money for player in self.players) < 100:
            self.active_players = list(self.players)  # reset active players for the round
            self.play_round(file)
        winner = max(self.players, key=lambda player: player.banked_money)
        file.write(f"{winner.name} wins with {winner.banked_money} points!\n")
        self.print_rankings(file)
        return self.get_game_state()

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





    
def run_simulation_many_times(number,score):
    
    all_players=get_all_player_classes_from_folder()
    if not all_players:
        raise ValueError("No player classes provided.")

    # Dictionary to store the number of wins for each player
    win_counts = {filename[:-3]: 0 for _, filename in all_players}

    current_time = time.strftime("%Y-%m-%d_%H-%M-%S")

    # Create a filename using the number of simulations and the current time
    filename = f"game_simulation_{number}_runs_{current_time}.txt"
    
    with open(filename, 'w') as file:
        for _ in range(number):
            game = Game(all_players)
            game_result = game.play_game(file)
            winner = max(game.players, key=lambda player: player.banked_money)
            win_counts[winner.name] += score

    # Print the results
    results = [f"{number} games were played"]
    for player_name, count in sorted(win_counts.items(), key=lambda item: item[1], reverse=True):
        results.append(f"{player_name} won {count} games")
    
    return "\n".join(results)

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
