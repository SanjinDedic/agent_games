import random
import os
import time
from abc import  abstractmethod

class Player():
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
        self.players = [PlayerClass(f"{filename[:-3]}", "abc123") for PlayerClass, filename in player_classes]
        self.active_players = list(self.players)
        self.dice = Dice()

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

            # If roll is 1, all players lose unbanked money and the round ends
            if roll == 1:
                for player in self.active_players:
                    player.reset_unbanked_money()
                    print('---------TURN END----------')
                break

            # Process each player's turn
            for player in self.active_players:
                if not player.has_banked_this_turn:
                    player.unbanked_money += roll
                    decision = player.make_decision(self.get_game_state())
                    if decision == 'bank':
                        player.bank_money()
                        player.has_banked_this_turn = True

                        # Check if the player has won after banking
                        if player.banked_money >= 100:
                            print('---------TURN END----------')
                            return  # End the round if a player has won

            # Check if all players have banked, then end the round
            if all(player.has_banked_this_turn for player in self.active_players):
                print('---------TURN END----------')
                break


    def play_game(self):
        while max(player.banked_money for player in self.players) < 100:
            self.active_players = list(self.players)  # reset active players for the round
            self.play_round()
        winner = max(self.players, key=lambda player: player.banked_money)
        return winner.name, winner.banked_money

    def print_rankings(self):
        ranked_players = sorted(self.players, key=lambda player: player.banked_money, reverse=True)
        points_dict = {player.name: 5 - i for i, player in enumerate(ranked_players)}
        for i in range(len(ranked_players) - 1):
            if ranked_players[i].banked_money == ranked_players[i + 1].banked_money:
                tied_point = max(1, points_dict[ranked_players[i + 1].name])
                points_dict[ranked_players[i].name] = tied_point
        return points_dict

def run_simulation_many_times(number):
    all_players = get_all_player_classes_from_folder()
    if not all_players:
        raise ValueError("No player classes provided.")

    total_points = {filename[:-3]: 0 for _, filename in all_players}
    for _ in range(number):
        game = Game(all_players)
        _, _ = game.play_game()
        final_scores = game.print_rankings()
        for player, points in final_scores.items():
            total_points[player] += points

    results = [f"{number} games were played"]
    for player_name in sorted(total_points, key=total_points.get, reverse=True):
        results.append(f"{player_name} earned a total of {total_points[player_name]} points")
    
    return "\n".join(results)

class Player11111(Player):
    def make_decision(self, game_state):
        threshold = 22
        if game_state['unbanked_money'][self.name] >= threshold:
            print(self.name, 'banking threshold is',threshold,'Unbanked money:', game_state['unbanked_money'][self.name])
            return 'bank'
        return 'continue'

class Player22222(Player):
    def make_decision(self, game_state):
        threshold = 5
        if game_state['unbanked_money'][self.name] >= threshold:
            print(self.name, 'banking threshold is',threshold,'Unbanked money:', game_state['unbanked_money'][self.name])
            return 'bank'
        return 'continue'

class Player33333(Player):
    def make_decision(self, game_state):
        threshold = 12
        if game_state['unbanked_money'][self.name] >= threshold:
            print(self.name, 'banking threshold is',threshold,'Unbanked money:', game_state['unbanked_money'][self.name])
            return 'bank'
        return 'continue'

class Player44444(Player):
    def make_decision(self, game_state):
        if game_state['unbanked_money'][self.name] >= 31:
            return 'bank'
        return 'continue'
   



def get_all_player_classes_from_folder():
    return [(Player11111, "Player11111.py"), (Player22222, "Player22222.py"), (Player33333, "Player33333.py"), (Player44444, "Player44444.py")]

if __name__ == "__main__":
    print(run_simulation_many_times(1000))
