from abc import ABC, abstractmethod
from typing import Dict


class Player(ABC):
    def __init__(self):
        self.name = self.__class__.__name__
        self.feedback = []
        # Set your character attributes here (each must be between 5 and 50)
        self.strength = 25  # Attribute that determines damage per strike
        self.defense = 25  # Damage reduction value
        self.dexterity = 25  # Dodge chance percentage
        self.vitality = 25  # attribute that determines health points

        #Attributes derived from stats
        self.create_derived_stats()

        # Game tracking attributes
        self.wins = 0
        self.losses = 0

        # Store original attributes after they're set
        self._store_original_attributes()

    def add_feedback(self, message):
        """Add feedback that will be visible in the game output"""
        self.feedback.append(message)
    
    def create_derived_stats(self):
        self.attack = self.strength*2 # Actual damage per strike (before defences or specific attacks are applied)
        self.max_health = self.vitality*5 # Health points
        self.health = self.max_health # this goes down during combat

    def level_up(self):
        """Player manages own leveling - add 1 to all attributes"""
        self.strength += 1
        self.defense += 1
        self.dexterity += 1
        self.vitality += 1
        self.create_derived_stats()
        

    def reset_to_original_stats(self):
        """Reset player to original attribute values"""
        if hasattr(self, "_original_attributes"):
            self.strength = self._original_attributes["strength"]
            self.defense = self._original_attributes["defense"]
            self.dexterity = self._original_attributes["dexterity"]
            self.vitality = self._original_attributes["vitality"]
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

    def _store_original_attributes(self):
        """Store original attributes for reset purposes"""
        self._original_attributes = {
            "strength": self.strength,
            "defense": self.defense,
            "dexterity": self.dexterity,
            "vitality": self.vitality,
        }

    @staticmethod
    def validate_action_for_role(action: str, role: str) -> bool:
        """Validate that the action is appropriate for the given role"""
        attack_actions = ["attack", "big_attack"]
        defense_actions = ["defend", "dodge", "run_away"]

        if role == "attacker":
            return action in attack_actions
        elif role == "defender":
            return action in defense_actions
        else:
            return False

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
