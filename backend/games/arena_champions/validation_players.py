from typing import Dict

from backend.games.arena_champions.player import Player


class NormalAttackNormalDefend(Player):
    """Always uses normal attack and defend - Balanced tank build"""

    def __init__(self):
        super().__init__()
        # Balanced tank: good defense and health to outlast opponents
        self.strength = 20
        self.defense = 40
        self.vitality = 35
        self.dexterity = 5
        self.create_derived_stats()
        self._store_original_attributes()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        # Validate role and return appropriate action
        if your_role == "attacker":
            self.add_feedback("Normal attack as attacker")
            return "attack"
        elif your_role == "defender":
            self.add_feedback("Defending with defense")
            return "defend"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class BigAttackNormalDefend(Player):
    """Always uses big attack and defend - Power tank build"""

    def __init__(self):
        super().__init__()
        # Power tank: high attack with good defense to survive big attack costs
        self.strength = 45
        self.defense = 30
        self.vitality = 20
        self.dexterity = 5
        self.create_derived_stats()
        self._store_original_attributes()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("Big attack as attacker")
            return "big_attack"
        elif your_role == "defender":
            self.add_feedback("Defending with defense")
            return "defend"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class NormalAttackDodge(Player):
    """Always uses normal attack and dodge - Agile fighter build"""

    def __init__(self):
        super().__init__()
        # Agile fighter: high dexterity for dodging, moderate attack
        self.strength = 30
        self.defense = 5
        self.vitality = 15
        self.dexterity = 50
        self.create_derived_stats()
        self._store_original_attributes()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("Normal attack as attacker")
            return "attack"
        elif your_role == "defender":
            self.add_feedback("Defending with dodge")
            return "dodge"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class BigAttackDodge(Player):
    """Always uses big attack and dodge - Glass cannon dodger build"""

    def __init__(self):
        super().__init__()
        # Glass cannon dodger: high attack and dexterity, low defense/health
        self.strength = 40
        self.defense = 5
        self.vitality = 15
        self.dexterity = 40
        self.create_derived_stats()
        self._store_original_attributes()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("Big attack as attacker")
            return "big_attack"
        elif your_role == "defender":
            self.add_feedback("Defending with dodge")
            return "dodge"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class NormalAttackRunAway(Player):
    """Always uses normal attack and run away - Survivalist build"""

    def __init__(self):
        super().__init__()
        # vitality and defense are useless when the only damage you ever take is 50% of your health, and dexterity is useless when the attacks/defenses you use don't require it. 
        self.strength = 50
        self.defense = 17
        self.vitality = 17
        self.dexterity = 16
        self.create_derived_stats()
        self._store_original_attributes()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("Normal attack as attacker")
            return "attack"
        elif your_role == "defender":
            self.add_feedback("Defending by running away")
            return "run_away"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class BigAttackRunAway(Player):
    """Always uses big attack and run away - Berserker build"""

    def __init__(self):
        super().__init__()
        # Max strength to take advantage of big attack. Defense, vitality, and dexterity do not matter at all (see normalattackrunaway)
        self.strength = 50
        self.defense = 17
        self.vitality = 17
        self.dexterity = 16
        self.create_derived_stats()
        self._store_original_attributes()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("Big attack as attacker")
            return "big_attack"
        elif your_role == "defender":
            self.add_feedback("Defending by running away")
            return "run_away"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class AdaptivePlayer(Player):
    """More complex player that adapts based on health, role, and opponent"""

    def __init__(self):
        super().__init__()
        # Balanced build with room for adaptation
        self.strength = 30
        self.defense = 25
        self.vitality = 25
        self.dexterity = 20
        self.create_derived_stats()
        self._store_original_attributes()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            # Offensive decision making
            health_percentage = self.health / self.max_health
            opponent_health_percentage = (
                opponent_stats["health"] / opponent_stats["max_health"]
            )

            if health_percentage > 0.7 and opponent_health_percentage < 0.4:
                self.add_feedback("Going for the kill with big attack")
                return "big_attack"
            elif health_percentage < 0.4:
                self.add_feedback("Playing it safe with normal attack")
                return "attack"
            else:
                self.add_feedback("Standard attack approach")
                return "attack"

        elif your_role == "defender":
            # Defensive decision making
            health_percentage = self.health / self.max_health

            if health_percentage < 0.25:
                self.add_feedback("Critical health - running away")
                return "run_away"
            elif last_opponent_action == "big_attack":
                self.add_feedback("Big attack incoming - attempting dodge")
                return "dodge"
            elif self.defense > 30:
                self.add_feedback("High defense - using defend")
                return "defend"
            else:
                self.add_feedback("Attempting to dodge")
                return "dodge"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


# Validation function to ensure actions match roles
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


# List of players to be used for validation games
players = [
    NormalAttackNormalDefend(),
    BigAttackNormalDefend(),
    NormalAttackDodge(),
    BigAttackDodge(),
    NormalAttackRunAway(),
    BigAttackRunAway(),
    AdaptivePlayer(),
]
