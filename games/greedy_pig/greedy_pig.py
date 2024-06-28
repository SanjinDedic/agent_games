from games.base_game import BaseGame
import random
import os
import time

class GreedyPigGame(BaseGame):
    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        self.active_players = list(self.players)
        self.players_banked_this_round = []
        self.round_no = 0
        self.roll_no = 0
        self.game_over = False
        
    def roll_dice(self):
        return random.randint(1, 6)

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

        while True:
            self.roll_no += 1
            roll = self.roll_dice()
            if self.verbose:
                print(f' Dice says {roll}')

            if roll == 1:
                if self.verbose:
                    print("  Oops! Rolled a 1. All players lose their unbanked money.")
                for player in self.active_players:
                    if player.unbanked_money > 0 and self.verbose:
                        print(f"    * {player.name} loses ${player.unbanked_money} of unbanked money.")
                    player.reset_unbanked_money()
                break

            for player in self.active_players.copy():
                if not player.has_banked_this_turn:
                    player.unbanked_money += roll
                    if self.verbose:
                        print(f"{player.name} now has ${player.unbanked_money} unbanked.")
                    decision = player.make_decision(self.get_game_state())
                    if decision == 'bank':
                        if self.verbose:
                            print(f"    * {player.name} decides to bank ${player.unbanked_money}.")
                        player.bank_money()
                        player.has_banked_this_turn = True
                        self.players_banked_this_round.append(player.name)
                        self.active_players.remove(player)

            for player in self.active_players:
                if player.banked_money + player.unbanked_money >= 100:
                    self.game_over = True
                    return

        for player in self.players:
            player.reset_turn()

    def play_game(self):
        random.shuffle(self.players)
        while not self.game_over:
            self.active_players = list(self.players)
            if self.verbose:
                print('\nSTART ROUND #' + str(self.round_no))
            self.play_round()
            if self.verbose:
                print('  END OF ROUND #' + str(self.round_no))
                print(self.get_game_state())
                for player in self.players:
                    print('  ' + player.name + ': $' + str(player.banked_money))

        game_state = self.get_game_state()
        results = self.assign_points(game_state)
        return results

    def assign_points(self, game_state):
        score_aggregate = {player: game_state['banked_money'][player] + game_state['unbanked_money'][player] for player in game_state['banked_money']}
        sorted_players = sorted(score_aggregate.items(), key=lambda x: x[1], reverse=True)
        
        points = {player[0]: len(score_aggregate) - i for i, player in enumerate(sorted_players)}
        
        # Handle ties
        for i in range(1, len(sorted_players)):
            if sorted_players[i][1] == sorted_players[i-1][1] and points[sorted_players[i][0]] < points[sorted_players[i-1][0]]:
                points[sorted_players[i][0]] = points[sorted_players[i-1][0]]

        return {"points": points, "score_aggregate": score_aggregate}

    def reset(self):
        super().reset()
        self.active_players = list(self.players)
        self.players_banked_this_round = []
        self.round_no = 0
        self.roll_no = 0
        self.game_over = False
        
        for player in self.players:
            player.banked_money = 0
            player.unbanked_money = 0
            player.has_banked_this_turn = False


def run_simulations(num_simulations, league):
    return BaseGame.run_simulations(num_simulations, GreedyPigGame, league)

def draw_table(rankings):
    os.system('clear')
    print("-" * 50)
    print(f"{'Player':^20} | {'Points':^10} | {'Rank':^10}")
    print("-" * 50)
    for rank, (player, points) in enumerate(rankings, start=1):
        print(f"{player:^20} | {points:^10} | {rank:^10}")
    print("-" * 50)
    time.sleep(0.3)

def animate_simulations(num_simulations, refresh_number, league):
    game = GreedyPigGame(league, verbose=True)
    total_points = {player.name: 0 for player in game.players}
    
    for i in range(1, num_simulations + 1):
        game.reset()
        results = game.play_game()
        
        for player, points in results["points"].items():
            total_points[player] += points
        
        if i % refresh_number == 0 or i == num_simulations:
            print(f"\nRankings after {i} simulations:")
            sorted_total_points = sorted(total_points.items(), key=lambda x: x[1], reverse=True)
            draw_table(sorted_total_points)
