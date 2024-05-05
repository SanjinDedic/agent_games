import random
import time

class Game:
    def __init__(self, player_classes):
        # Create player instances from the provided classes
        self.players = [PlayerClass(f"{filename[:-3]}", "abc123") for PlayerClass, filename in player_classes]
        self.active_players = list(self.players)
        self.players_banked_this_round = []
        self.round_no = 0
        self.roll_no = 0

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
    
    def play_round(self, verbose=False):
        self.players_banked_this_round = []
        self.round_no += 1
        roll = self.roll_dice()
        if verbose:
            print(' Dice says', roll)

        # If roll is 1, all players lose unbanked money and the round ends
        if roll == 1:
            if verbose:
                print("  Oops! Rolled a 1. All players lose their unbanked money.")
            for player in self.active_players:
                if player.unbanked_money > 0:
                    if verbose:
                        print(f"    * {player.name} loses ${player.unbanked_money} of unbanked money.")
                player.reset_unbanked_money()
        else:

            for player in self.active_players:
                if not player.has_banked_this_turn:
                    player.unbanked_money += roll
                    if verbose:
                        print(f"{player.name} now has ${player.unbanked_money} unbanked.")
                    decision = player.make_decision(self.get_game_state())
                    if decision == 'bank':
                        if verbose:
                            print(f"    * {player.name} decides to bank ${player.unbanked_money}.")
                        player.bank_money()
                        self.players_banked_this_round.append(player.name)
                        if player.banked_money >= 100:
                            #everyone's unbanked money should be added to be banked before ranking function
                            if verbose:
                                print(f"{player.name} has won the game with ${player.banked_money}!")
                            return player.name  # Game complete
                    elif verbose:
                        # Adding feedback for choosing to not bank
                        print(f"{player.name} chooses not to bank. Risking ${player.unbanked_money} on the next roll!")
    
        for player in self.active_players:
            player.reset_turn()  # Resetting the banking status at the start of each turn


    def play_game(self, verbose= False):
        #randomise the order of the players
        random.shuffle(self.players)
        while True:
            self.active_players = list(self.players)  # reset active players for the round
            if verbose:
                print('\nSTART ROUND #' + str(self.round_no))
            winner = self.play_round(verbose)
            if winner:
                if verbose:
                    print(f"\nGame Over: {winner} has won the game!")
                break
            if verbose:
                print('  END OF ROUND #' + str(self.round_no))
                for player in self.players:
                    print('  ' + player.name + ': $' + str(player.banked_money))
                #time.sleep(2)

        game_state = self.get_game_state()
        return game_state