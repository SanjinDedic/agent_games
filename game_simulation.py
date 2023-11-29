import random
import os
import time
import json
from player import Player
import importlib.util
from game import Game
from rich.console import Console
from rich.table import Table

class GameSimulation:
    def __init__(self, folder_name="test_classes"):
        self.folder_name = folder_name
        self.player_classes = self.get_all_player_classes_from_folder()
        self.team_colors = self.load_team_colors()

    def set_folder(self, folder_name):
        self.folder_name = folder_name
        self.player_classes = self.get_all_player_classes_from_folder()

    def load_team_colors(self):
        with open('colors.json', 'r') as file:
            data = json.load(file)
            team_colors = data['colors']
        return team_colors
    
    def run_simulation_many_times(self, number, verbose=False):
        if not self.player_classes:
            raise ValueError("No player classes provided.")

        total_points = {filename[:-3]: 0 for _, filename in self.player_classes}
        current_time = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"logfiles/game_simulation_{number}_runs_{current_time}.txt"
        start_time = time.time()

        for _ in range(number):
            game = Game(self.player_classes)
            game_result = game.play_game(verbose)
            points_this_game = self.assign_points(game_result)

            for player, points in points_this_game.items():
                total_points[player] += points

        results = self.format_results(total_points, start_time, number, filename)
        return "\n".join(results) if self.folder_name == "classes" else total_points
    
    def run_simulation_with_animation(self, number, refresh_rate=200, verbose=False, folder_name="test_classes"):
        if not self.player_classes:
            raise ValueError("No player classes provided.")

        total_points = {filename[:-3]: 0 for _, filename in self.player_classes}
        games_won = {filename[:-3]: 0 for _, filename in self.player_classes}
        top_5_finishes = {filename[:-3]: 0 for _, filename in self.player_classes}
        games_played = {filename[:-3]: 0 for _, filename in self.player_classes}
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")

        # Add columns to the table
        table.add_column("Player", justify="right", style="bold")
        table.add_column("Total Points", justify="right")
        table.add_column("Games Won", justify="right")
        table.add_column("Top 5", justify="right")
        table.add_column("Games Played", justify="right")
        current_time = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"logfiles/game_simulation_{number}_runs_{current_time}.txt"
        start_time = time.time()
        
        colors = dict()
    
        game = Game(self.player_classes)
        for player in game.players:
            colors[player.name] = self.team_colors[game.players.index(player)%len(self.team_colors)]

        for i in range(number):
            game = Game(self.player_classes)
            for player in game.players:
                player.color = self.team_colors[i%len(self.team_colors)]

            game_result = game.play_game(verbose)
            points_this_game = self.assign_points(game_result)

            for player, points in points_this_game.items():
                total_points[player] += points
                games_played[player] += 1
                # Assuming you have a way to determine if a game is won or lost
                if game_result['banked_money'][player] > 100:
                    games_won[player] += 1

            top_5_players = sorted(points_this_game, key=points_this_game.get, reverse=True)[:5]
            for player in top_5_players:
                top_5_finishes[player] += 1            

            if (i + 1) % refresh_rate == 0 or i == number - 1:
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Player", justify="right", style="bold")
                table.add_column("Total Points", justify="right")
                table.add_column("Games Won", justify="right")
                table.add_column("Top 5", justify="right")
                table.add_column("Games Played", justify="right")
                for player_name in sorted(total_points, key=total_points.get, reverse=True):
                    table.add_row(player_name, 
                                str(total_points[player_name]), 
                                str(games_won[player_name]),
                                str(top_5_finishes[player_name]),
                                str(games_played[player_name]),
                                style=colors[player_name])
                                #check all players in game.players and if player_name is in there then use that color

                            

                console.clear()
                console.print(table)
                time.sleep(0.3)

        results = self.format_results(total_points, start_time, number, filename)
        return "\n".join(results) if self.folder_name == "classes" else total_points

    def assign_points(self, game_result, max_score=6):
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

        #if a player finishes first and its not a tie then they get extra points (8 in total)
        if points_distribution[sorted_scores[0][0]] != points_distribution[sorted_scores[1][0]]:
            points_distribution[sorted_scores[0][0]] = 8
        
        #if a player has the same amount of banked money as another player and they have more than one point they get deducted a point
        balances = [i[1] for i in sorted_scores]
        for player in banked_money:
            if balances.count(banked_money[player]) > 1 and points_distribution[player] >= 1:
                points_distribution[player] -= 1

        return points_distribution

    def get_all_player_classes_from_folder(self):
        # Get a list of all .py files in the given folder
        #check if a folder called classes exists otherwise use the present working directory
        if os.path.exists(self.folder_name):
            main_folder_name = self.folder_name
        else:
            main_folder_name = os.getcwd()


        files = [f for f in os.listdir(main_folder_name) if os.path.isfile(os.path.join(main_folder_name, f)) and f.endswith('.py')]

        player_classes = []

        for file in files:
            module_name = file[:-3]  # remove the ".py" extension
            spec = importlib.util.spec_from_file_location(module_name, os.path.join(main_folder_name, file))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Check each item in the module to see if it's a subclass of Player
            for name, obj in vars(module).items():
                if isinstance(obj, type) and issubclass(obj, Player) and obj is not Player:
                    player_classes.append((obj, file))
        return player_classes

    def format_results(self, total_points, start_time, number, filename):
        results = [f"{number} games were played in {round(time.time() - start_time, 2)} seconds"]
        for player_name in sorted(total_points, key=total_points.get, reverse=True):
            results.append(f"{player_name} earned a total of {total_points[player_name]} points")

        if self.folder_name == "classes":
            with open(filename, 'w') as file:
                g_res = {"banked_money": total_points}
                scores = self.assign_points(g_res, max_score=21)
                for player_name in sorted(scores, key=scores.get, reverse=True):
                    file.write(f"{player_name} earned a total of {scores[player_name]*20} points\n")
                file.write("\n")
                file.write("----------------------------\n")
                file.write("\n".join(results))

        return results

if __name__=="__main__":
    simulation = GameSimulation()
    results = simulation.run_simulation_many_times(100, verbose=False)
    print(results)