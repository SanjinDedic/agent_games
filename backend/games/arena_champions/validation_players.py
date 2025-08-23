from typing import Dict
import random

from backend.games.arena_champions.player import Player


class AttackDefend(Player):
    """Uses attack and defend"""

    def __init__(self):
        super().__init__()
        self.strength_p = 0.25  # Attribute that determines damage per strike
        self.defense_p = 0.25  # Damage reduction value
        self.dexterity_p = 0.25  # Dodge chance percentage
        self.health_points_p = 0.25  # attribute that determines health points
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("Using attack")
            return "attack"
        elif your_role == "defender":
            self.add_feedback("Using defend")
            return "defend"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class AttackDodge(Player):
    """Uses attack and dodge"""

    def __init__(self):
        super().__init__()
        self.strength_p = 0.25  # Attribute that determines damage per strike
        self.defense_p = 0.25  # Damage reduction value
        self.dexterity_p = 0.25  # Dodge chance percentage
        self.health_points_p = 0.25  # attribute that determines health points
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("Using attack")
            return "attack"
        elif your_role == "defender":
            self.add_feedback("Using dodge")
            return "dodge"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class AttackBrace(Player):
    """Uses attack and brace"""

    def __init__(self):
        super().__init__()
        self.strength_p = 0.25  # Attribute that determines damage per strike
        self.defense_p = 0.25  # Damage reduction value
        self.dexterity_p = 0.25  # Dodge chance percentage
        self.health_points_p = 0.25  # attribute that determines health points
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("Using attack")
            return "attack"
        elif your_role == "defender":
            self.add_feedback("Using brace")
            return "brace"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class BigAttackDefend(Player):
    """Uses big_attack and defend"""

    def __init__(self):
        super().__init__()
        self.strength_p = 0.25  # Attribute that determines damage per strike
        self.defense_p = 0.25  # Damage reduction value
        self.dexterity_p = 0.25  # Dodge chance percentage
        self.health_points_p = 0.25  # attribute that determines health points
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("Using big_attack")
            return "big_attack"
        elif your_role == "defender":
            self.add_feedback("Using defend")
            return "defend"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class BigAttackDodge(Player):
    """Uses big_attack and dodge"""

    def __init__(self):
        super().__init__()
        self.strength_p = 0.25  # Attribute that determines damage per strike
        self.defense_p = 0.25  # Damage reduction value
        self.dexterity_p = 0.25  # Dodge chance percentage
        self.health_points_p = 0.25  # attribute that determines health points
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("Using big_attack")
            return "big_attack"
        elif your_role == "defender":
            self.add_feedback("Using dodge")
            return "dodge"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class BigAttackBrace(Player):
    """Uses big_attack and brace"""

    def __init__(self):
        super().__init__()
        self.strength_p = 0.25  # Attribute that determines damage per strike
        self.defense_p = 0.25  # Damage reduction value
        self.dexterity_p = 0.25  # Dodge chance percentage
        self.health_points_p = 0.25  # attribute that determines health points
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("Using big_attack")
            return "big_attack"
        elif your_role == "defender":
            self.add_feedback("Using brace")
            return "brace"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class PreciseAttackDefend(Player):
    """Uses precise_attack and defend"""

    def __init__(self):
        super().__init__()
        self.strength_p = 0.25  # Attribute that determines damage per strike
        self.defense_p = 0.25  # Damage reduction value
        self.dexterity_p = 0.25  # Dodge chance percentage
        self.health_points_p = 0.25  # attribute that determines health points
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("Using precise_attack")
            return "precise_attack"
        elif your_role == "defender":
            self.add_feedback("Using defend")
            return "defend"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class PreciseAttackDodge(Player):
    """Uses precise_attack and dodge"""

    def __init__(self):
        super().__init__()
        self.strength_p = 0.25  # Attribute that determines damage per strike
        self.defense_p = 0.25  # Damage reduction value
        self.dexterity_p = 0.25  # Dodge chance percentage
        self.health_points_p = 0.25  # attribute that determines health points
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("Using precise_attack")
            return "precise_attack"
        elif your_role == "defender":
            self.add_feedback("Using dodge")
            return "dodge"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class PreciseAttackBrace(Player):
    """Uses precise_attack and brace"""

    def __init__(self):
        super().__init__()
        self.strength_p = 0.25  # Attribute that determines damage per strike
        self.defense_p = 0.25  # Damage reduction value
        self.dexterity_p = 0.25  # Dodge chance percentage
        self.health_points_p = 0.25  # attribute that determines health points
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("Using precise_attack")
            return "precise_attack"
        elif your_role == "defender":
            self.add_feedback("Using brace")
            return "brace"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


# List of players to be used for validation games
players = [
    AttackDefend(),
    AttackDodge(),
    AttackBrace(),
    BigAttackDefend(),
    BigAttackDodge(),
    BigAttackBrace(),
    PreciseAttackDefend(),
    PreciseAttackDodge(),
    PreciseAttackBrace(),
]
