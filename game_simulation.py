import random
import os
import time
import json
from player import Player
import importlib.util
from greedy_pig import Game
from rich.console import Console
from rich.table import Table
from config import CURRENT_DIR

class GameSimulation:
    def __init__(self, folder_name="leagues/test_league"):
        self.folder_name = folder_name
        self.player_classes = []  # Initialize player_classes as an empty list
        self.team_colors = self.load_team_colors()
        self.player_classes = self.get_all_player_classes_from_folder()
        

    def set_folder(self, folder_name):
        self.folder_name = folder_name
        self.player_classes = self.get_all_player_classes_from_folder()

    def load_team_colors(self):
        with open(os.path.join(CURRENT_DIR, 'colors.json'), 'r') as file:
            data = json.load(file)
            team_colors = data['colors']
        return team_colors

    def run_simulation_many_times(self, number, verbose=False):
        if not self.player_classes:
            raise ValueError("No player classes provided.")
        total_points = {filename[:-3]: 0 for _, filename in self.player_classes}

        for _ in range(number):
            game = Game(self.player_classes)
            game_result = game.play_game(verbose)
            points_this_game = self.assign_points(game_result)

            for player, points in points_this_game.items():
                total_points[player] += points

        results = self.format_results(total_points, number)
        return "\n".join(results) if self.folder_name == "classes" else total_points

    def run_simulation_with_animation(self, number, refresh_rate=200, verbose=False):
        if not self.player_classes:
            raise ValueError("No player classes provided.")

        total_points = {filename[:-3]: 0 for _, filename in self.player_classes}
        games_won = {filename[:-3]: 0 for _, filename in self.player_classes}
        top_5_finishes = {filename[:-3]: 0 for _, filename in self.player_classes}
        games_played = {filename[:-3]: 0 for _, filename in self.player_classes}
        console = Console()
        colors = dict()

        game = Game(self.player_classes)
        for player in game.players:
            colors[player.name] = self.team_colors[game.players.index(
                player) % len(self.team_colors)]

        for i in range(number):
            game = Game(self.player_classes)
            for player in game.players:
                player.color = self.team_colors[i % len(self.team_colors)]

            game_result = game.play_game(verbose)
            winner = game_result.get('winner')  # Get the winner's name from the game result
            points_this_game = self.assign_points(game_result)

            for player, points in points_this_game.items():
                total_points[player] += points
                games_played[player] += 1
                if winner == player:  # Check if the player's name matches the winner's name
                    games_won[player] += 1

            top_5_players = sorted(points_this_game, key=points_this_game.get, reverse=True)[:5]
            for player in top_5_players:
                top_5_finishes[player] += 1
            game_status = total_points, games_won, top_5_finishes, games_played, colors
            self.print_table(game_status, console, refresh_rate, i, number)

        if self.folder_name == "classes":
            self.log_results(number, total_points)

    def assign_points(self, game_result):
        banked_money = game_result['banked_money']
        sorted_scores = sorted(banked_money.items(), key=lambda x: x[1], reverse=True)
        
        points_distribution = {player: 0 for player in banked_money}
        
        if len(sorted_scores) >= 1:
            points_distribution[sorted_scores[0][0]] = 3  # First place gets 3 points
        
        if len(sorted_scores) >= 2:
            points_distribution[sorted_scores[1][0]] = 2  # Second place gets 2 points
        
        if len(sorted_scores) >= 3:
            points_distribution[sorted_scores[2][0]] = 1  # Third place gets 1 point
        
        return points_distribution


    def get_all_player_classes_from_folder(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        league_directory = os.path.join(current_dir, self.folder_name)

        print("Current directory:", current_dir)
        print("Main folder name:", league_directory)

        if not os.path.exists(league_directory):
            print(f"The folder '{league_directory}' does not exist.")
            return []

        print("Files and directories in the league folder:")
        player_classes = []
        for item in os.listdir(league_directory):
            print(item)
            if item.endswith(".py"):
                print(f"Found a Python file: {item}")
                module_name = item[:-3]  # Remove the '.py' extension
                module_path = os.path.join(league_directory, item)
                print(f"Module name: {module_name}")
                print(f"Module path: {module_path}")
                
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                print(f"Loaded module: {module}")
                print(f"Module attributes: {dir(module)}")
                
                if hasattr(module, "CustomPlayer"):
                    player_class = getattr(module, "CustomPlayer")
                    print(f"Found CustomPlayer class: {player_class}")
                    player = player_class(module_name, "abc123")
                    print(f"Created player instance: {player}")
                    player_classes.append((player, item))
                else:
                    print(f"CustomPlayer class not found in module: {module_name}")

        print(f"Found {len(player_classes)} player classes.")
        return player_classes

    def print_table(self, game_status, console, refresh_rate, i, number):
        total_points, games_won, top_5_finishes, games_played, colors = game_status
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
                              style=colors.get(player_name, ""))

            console.clear()
            console.print(table)
            time.sleep(0.3)

    def format_results(self, total_points, number):
        results = [f"{number} games were played"]
        for player_name in sorted(total_points, key=total_points.get, reverse=True):
            results.append(f"{player_name} earned a total of {total_points[player_name]} points")
        return results

    def log_results(self, number, total_points):
        current_time = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"logfiles/game_simulation_{number}_runs_{current_time}.txt"
        with open(filename, 'w') as file:
            g_res = {"banked_money": total_points}
            scores = self.assign_points(g_res, max_score=21)
            for player_name in sorted(scores, key=scores.get, reverse=True):
                file.write(f"{player_name} earned a total of {scores[player_name]*20} points\n")
            file.write("\n")
            file.write("----------------------------\n")
            file.write("\n".join(self.format_results(total_points, number)))


if __name__ == "__main__":
    simulation = GameSimulation()
    #results = simulation.run_simulation_many_times(1, verbose=True)
    results = simulation.run_simulation_with_animation(5000, verbose=False)
    print(results)



'''
def assign_points(self, game_result, max_score=6):
        banked_money = game_result['banked_money']
        sorted_scores = sorted(banked_money.items(), key=lambda x: x[1], reverse=True)
        points_distribution = {}
        last_score = None
        last_rank = 0

        if len(sorted_scores) == 1:  # Only one player, assign maximum points
            points_distribution[sorted_scores[0][0]] = max_score
            return points_distribution

        for rank, (player, score) in enumerate(sorted_scores, start=1):
            if score != last_score:  # New score, update rank
                last_rank = rank
            last_score = score

            # Assign points based on rank
            points = max(max_score - last_rank, 0)
            points_distribution[player] = points

        # if a player finishes first and its not a tie then they get extra points (8 in total)
        if points_distribution[sorted_scores[0][0]] != points_distribution[sorted_scores[1][0]]:
            points_distribution[sorted_scores[0][0]] = 8

        # if a player has the same amount of banked money as another player and they have more than one point they get deducted a point
        balances = [i[1] for i in sorted_scores]
        for player in banked_money:
            if balances.count(banked_money[player]) > 1 and points_distribution[player] >= 1:
                points_distribution[player] -= 1

        return points_distribution
'''