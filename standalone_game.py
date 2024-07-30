import random

class Player:
    def __init__(self, name, limit):
        self.name = name
        self.limit = limit
        self.banked_money = 0
        self.unbanked_money = 0
        self.has_banked_this_turn = False

    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] >= self.limit:
            return 'bank'
        return 'continue'

    def reset_unbanked_money(self):
        self.unbanked_money = 0

    def bank_money(self):
        self.banked_money += self.unbanked_money
        self.reset_unbanked_money()

    def reset_turn(self):
        self.has_banked_this_turn = False

class GreedyPigGame:
    def __init__(self, players):
        self.players = players
        self.active_players = list(players)
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
            print(f'Dice says {roll}')

            if roll == 1:
                print("Oops! Rolled a 1. All players lose their unbanked money.")
                for player in self.active_players:
                    if player.unbanked_money > 0:
                        print(f"  * {player.name} loses ${player.unbanked_money} of unbanked money.")
                    player.reset_unbanked_money()
                break

            for player in self.active_players.copy():
                if not player.has_banked_this_turn:
                    player.unbanked_money += roll
                    print(f"{player.name} now has ${player.unbanked_money} unbanked.")
                    decision = player.make_decision(self.get_game_state())
                    if decision == 'bank':
                        print(f"  * {player.name} decides to bank ${player.unbanked_money}.")
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
            print(f'\nSTART ROUND #{self.round_no + 1}')
            self.play_round()
            print(f'END OF ROUND #{self.round_no}')
            for player in self.players:
                print(f'  {player.name}: ${player.banked_money}')

        print("\nGame Over!")
        winner = max(self.players, key=lambda p: p.banked_money)
        print(f"The winner is {winner.name} with ${winner.banked_money}!")

def main():
    players = [
        Player("AlwaysBank", 1),
        Player("Bank5", 5),
        Player("Bank6", 6),
        Player("Bank7", 7),
        Player("Bank10", 10),
        Player("Bank15", 15),
        Player("Bank20", 20),
        Player("Bank25", 25),
        Player("Bank30", 30),
        Player("Bank35", 35),
        Player("Bank40", 40),
        Player("Bank45", 45),
        Player("Bank50", 50)
    ]

    game = GreedyPigGame(players)
    game.play_game()

if __name__ == "__main__":
    main()