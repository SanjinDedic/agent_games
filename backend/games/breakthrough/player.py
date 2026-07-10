from abc import ABC, abstractmethod


class Player(ABC):
    def __init__(self):
        self.name = self.__class__.__name__
        self.feedback = []
        self.role = None  # "attacker" or "defender", set by the game each match

    def add_feedback(self, message):
        """Add feedback that will be visible in the game output"""
        self.feedback.append(message)

    @abstractmethod
    def make_decision(self, game_state):
        """
        Decide your move for this turn. Both players decide simultaneously.

        Args:
            game_state (dict): Contains:
                - turn (int): Current turn number (1..move_cap)
                - role (str): "attacker" or "defender"
                - my_pos (tuple): Your (x, y). x=0 is the left edge,
                  x=grid_size-1 is the right edge (the attacker's goal)
                - opp_pos (tuple): Opponent's (x, y)
                - my_boosts (int): Boosts you have left
                - opp_boosts (int): Boosts your opponent has left
                - my_mines (int): Mines you have left to lay (start with 1)
                - opp_mines (int): Mines your opponent has left to lay
                - my_mine (tuple or None): Where your laid mine sits
                  (the opponent's mine position is hidden from you)
                - opp_frozen (bool): True once the opponent has been blown
                  up by your mine — they can never move again
                - my_trace (list): Every cell you have visited, in order
                - opp_trace (list): Every cell your opponent has visited
                - grid_size (int): Board is grid_size x grid_size
                - move_cap (int): Match ends in a timeout after this many turns

        Returns:
            str or dict: A direction "N", "S", "E", "W" or "STAY",
            or {"direction": "E", "boost": True} to spend a boost and
            jump 2 cells in that direction (jumping over the middle cell),
            or {"direction": "N", "mine": True} to lay a mine on the cell
            you are leaving. An opponent who ends a move on your mine is
            blown up and cannot move for the rest of the match. Your own
            mine never hurts you.
        """
        pass
