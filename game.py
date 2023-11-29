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
        self.roll_no = 0
        for player in self.active_players:
            player.reset_turn()  # Resetting the banking status at the start of each turn

        while True:
            self.roll_no += 1
            roll = self.roll_dice()
            if verbose:
                print('  ROLL #' + str(self.roll_no) + ':', 'Dice says', roll)
            # If roll is 1, all players lose unbanked money and the round ends
            if roll == 1:
                for player in self.active_players:
                    player.reset_unbanked_money()
                break

            # Process each player's turn
            for player in self.active_players:
                if not player.has_banked_this_turn:
                    player.unbanked_money += roll
                    decision = player.make_decision(self.get_game_state())
                    if decision == 'bank':
                        if verbose:
                            print('    *', player.name, 'banked $' + str(player.unbanked_money))
                        player.bank_money()
                        player.has_banked_this_turn = True
                        self.players_banked_this_round.append(player.name)
                        # Check if the player has won after banking
                        if player.banked_money >= 100:
                            return  # End the round if a player has won

            # Check if all players have banked, then end the round
            if all(player.has_banked_this_turn for player in self.active_players):
                break

    def play_game(self, verbose= False):
        #randomise the order of the players
        random.shuffle(self.players)
        while max(player.banked_money for player in self.players) < 100:
            self.active_players = list(self.players)  # reset active players for the round
            if verbose:
                print('\nSTART ROUND #' + str(self.round_no))
            self.play_round(verbose)
            if verbose:
                print('\n  END OF ROUND')
                for player in self.players:
                    print('  ' + player.name + ': $' + str(player.banked_money))
                time.sleep(2)

        game_state = self.get_game_state()
        return game_state