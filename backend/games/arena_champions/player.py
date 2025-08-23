from abc import ABC, abstractmethod
from typing import Dict


class Player(ABC):
    def __init__(self):
        self.name = self.__class__.__name__
        self.feedback = []

        # set the proportions attributes use here (each must be between 0.05 and 0.5)
        self.attack_proportion = 0.25  # Attribute that determines damage per strike
        self.defense_proportion = 0.25  # Damage reduction value
        self.dexterity_proportion = 0.25  # Dodge chance percentage
        self.max_health_proportion = 0.25  # attribute that determines max health points
        # Set your character attributes here (each must be between 5 and 50)
        self.set_to_original_stats()

        # Game tracking attributes
        self.wins = 0
        self.losses = 0

    def add_feedback(self, message):
        """Add feedback that will be visible in the game output"""
        self.feedback.append(message)

    def create_derived_stats(self):
        self.health = self.max_health  # this goes down during combat
        self.defense = self.defense

    def level_up(self, level_up_amount=1):
        """Player manages own leveling - add 1 distributed amoung all attributes"""
        self.strength += level_up_amount * self.attack_proportion
        self.defense += level_up_amount * self.defense_proportion
        self.dexterity += level_up_amount * self.dexterity_proportion
        self.max_health += level_up_amount * self.max_health_proportion
        self.create_derived_stats()

    def set_to_original_stats(self):
        """Set player to original attribute values"""
        self.attack = (
            2 * 100 * self.attack_proportion
        )  # Actual damage per strike (before defences or specific attacks are applied)
        self.strength = (
            100 * self.attack_proportion
        )  # Attribute that determines damage per strike
        self.defense = 100 * self.defense_proportion  # Damage reduction value
        self.dexterity = 100 * self.dexterity_proportion  # Dodge chance percentage
        self.max_health = 1000 * self.max_health_proportion  # Maximum health points
        self.create_derived_stats()

    def get_combat_info(self):
        """Return minimal combat information"""
        return {
            "attack": self.attack,
            "defense": self.defense,
            "dexterity": self.dexterity,
            "health": self.health,
            "max_health": self.max_health,
        }

    @abstractmethod
    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        """
        Make a combat decision based on current battle state and your role.

        Args:
            opponent_stats: Dictionary containing opponent's stats (attack, defense, dexterity, health, max_health)
            turn: Current turn number
            your_role: Either "attacker" (your turn to attack) or "defender" (your turn to defend)
            last_opponent_action: Opponent's last action (if any)

        Returns:
            One of:
            - If your_role == "attacker": 'attack', 'big_attack'
            - If your_role == "defender": 'defend', 'dodge', 'run_away'

            Attack Actions (only valid when your_role == "attacker"):
            - 'attack': Normal damage based on attack stat
            - 'big_attack': Double damage but lose 50% of current health

            Defense Actions (only valid when your_role == "defender"):
            - 'defend': Reduce incoming damage by defense percentage
            - 'dodge': Attempt to completely avoid damage (dexterity% chance)
            - 'run_away': Lose 50% health but become immune to this attack
        """
        pass
