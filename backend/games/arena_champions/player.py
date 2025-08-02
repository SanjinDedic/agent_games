from abc import ABC, abstractmethod
from typing import Dict


class Player(ABC):
    def __init__(self):
        self.name = self.__class__.__name__
        self.feedback = []
        # Set your character attributes here (each must be between 5 and 50)
        self.attack = 25  # Damage per strike
        self.defense = 25  # Damage reduction percentage
        self.dexterity = 25  # Dodge chance percentage
        self.health = 25  # Health points

    def add_feedback(self, message):
        """Add feedback that will be visible in the game output"""
        self.feedback.append(message)

    @abstractmethod
    def make_combat_decision(self, combat_state: Dict) -> str:
        """
        Make a combat decision based on current battle state.

        Args:
            combat_state: Dictionary containing:
                - my_current_hp: Your current HP
                - my_max_hp: Your maximum HP
                - my_attack: Your attack stat
                - my_defense: Your defense stat
                - my_dexterity: Your dexterity stat
                - turns_elapsed: Number of turns so far
                - last_opponent_action: Opponent's last action (if any)
                - my_status: 'normal' or other status effects
                - has_preview: Whether you can see opponent stats
                - opponent_stats (if has_preview): Dict with attack, defense, hp, current_hp, dexterity

        Returns:
            One of: 'attack', 'big_attack', 'defend', 'dodge', 'run_away'

            Attack Actions:
            - 'attack': Normal damage based on attack stat
            - 'big_attack': Double damage but lose 50% of current health

            Defense Actions:
            - 'defend': Reduce incoming damage by defense percentage
            - 'dodge': Attempt to completely avoid damage (dexterity% chance)
            - 'run_away': Lose 50% health but take no damage this turn
        """
        pass
