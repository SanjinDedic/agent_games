from typing import Dict
import random

from backend.games.arena_champions.player import Player


class NormalAttackNormalDefend(Player):
    """Always uses normal attack and defend - Balanced tank build"""

    def __init__(self):
        super().__init__()
        # Balanced tank: good defense and health to outlast opponents
        self.strength_p = 0.20
        self.defense_p = 0.40
        self.health_points_p = 0.35
        self.dexterity_p = 0.05
        self.set_to_original_stats()

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
        self.strength_p = 0.45
        self.defense_p = 0.30
        self.health_points_p = 0.20
        self.dexterity_p = 0.05
        self.set_to_original_stats()

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

class MultiattackNormalDefend(Player):
    """Always uses multiattack and defend"""

    def __init__(self):
        super().__init__()
        # Higher dexterity and defence to take advantage of its moves, no strength, low health_points
        self.strength_p = 0.05
        self.defense_p = 0.35
        self.health_points_p = 0.15
        self.dexterity_p = 0.45
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        # Validate role and return appropriate action
        if your_role == "attacker":
            self.add_feedback("multiattack as attacker")
            return "multiattack"
        elif your_role == "defender":
            self.add_feedback("Defending with defense")
            return "defend"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )

class PreciseAttackNormalDefend(Player):
    """Always uses precise attack and defend"""

    def __init__(self):
        super().__init__()
        # High dexterity to use precise attack well, moderate defense and attack, low health_points
        self.strength_p = 0.25
        self.defense_p = 0.25
        self.health_points_p = 0.15
        self.dexterity_p = 0.40
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        # Validate role and return appropriate action
        if your_role == "attacker":
            self.add_feedback("Precise attack as attacker")
            return "precise_attack"
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
        self.strength_p = 0.30
        self.defense_p = 0.05
        self.health_points_p = 0.15
        self.dexterity_p = 0.50
        self.set_to_original_stats()

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
        self.strength_p = 0.40
        self.defense_p = 0.05
        self.health_points_p = 0.15
        self.dexterity_p = 0.40
        self.set_to_original_stats()

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

class MultiattackDodge(Player):
    """Always uses multiattack and dodge"""

    def __init__(self):
        super().__init__()
        # max dexterity for really high damage and dodge, moderate non-dexterity defensive stats, no strength
        self.strength_p = 0.05
        self.defense_p = 0.20
        self.health_points_p = 0.25
        self.dexterity_p = 0.50
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("multiattack as attacker")
            return "multiattack"
        elif your_role == "defender":
            self.add_feedback("Defending with dodge")
            return "dodge"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )

class PreciseAttackDodge(Player):
    """Always uses precise attack and dodge"""

    def __init__(self):
        super().__init__()
        # high dexterity for dodging and precise attack, moderate health_points, low other stats
        self.strength_p = 0.15
        self.defense_p = 0.05
        self.health_points_p = 0.30
        self.dexterity_p = 0.50
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("Precise attack as attacker")
            return "precise_attack"
        elif your_role == "defender":
            self.add_feedback("Defending with dodge")
            return "dodge"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )

class NormalAttackBrace(Player):
    """Always uses normal attack and brace - Survivalist build"""

    def __init__(self):
        super().__init__()
        # health_points and defense are less important, and dexterity is useless when the attacks/defenses you use don't require it.
        self.strength_p = 0.50
        self.defense_p = 0.20
        self.health_points_p = 0.25
        self.dexterity_p = 0.05
        self.set_to_original_stats()

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
            self.add_feedback("Defending by bracing")
            return "brace"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class BigAttackBrace(Player):
    """Always uses big attack and brace - Berserker build"""

    def __init__(self):
        super().__init__()
        # Max strength to take advantage of big attack. Defense, health_points, and dexterity don't matter much
        self.strength_p = 0.50
        self.defense_p = 0.24
        self.health_points_p = 0.21
        self.dexterity_p = 0.05
        self.set_to_original_stats()

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
            self.add_feedback("Defending by bracing")
            return "brace"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )

class MultiattackBrace(Player):
    """Always uses multiattack and brace"""

    def __init__(self):
        super().__init__()
        # very high dexterity, moderate defensive stats, no strength
        self.strength_p = 0.05
        self.defense_p = 0.25
        self.health_points_p = 0.20
        self.dexterity_p = 0.50
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("multiattack as attacker")
            return "multiattack"
        elif your_role == "defender":
            self.add_feedback("Defending by bracing")
            return "brace"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )

class PreciseAttackBrace(Player):
    """Always uses precise attack and brace"""

    def __init__(self):
        super().__init__()
        # higher dex to succeed in precise attacks and higher attack to still do damage
        self.strength_p = 0.40
        self.defense_p = 0.15
        self.health_points_p = 0.15
        self.dexterity_p = 0.30
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        if your_role == "attacker":
            self.add_feedback("Precise attack as attacker")
            return "precise_attack"
        elif your_role == "defender":
            self.add_feedback("Defending by bracing")
            return "brace"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )

class AdaptivePlayer(Player):
    """More complex player that adapts based on health, role, and opponent"""

    def __init__(self):
        super().__init__()
        # Balanced build with room for adaptation
        self.strength_p = 0.30
        self.defense_p = 0.25
        self.health_points_p = 0.25
        self.dexterity_p = 0.20
        self.set_to_original_stats()

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
                self.add_feedback("Critical health - bracing")
                return "brace"
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

class HighStrengthRandomMoves(Player):
    """Uses random moves"""

    def __init__(self):
        super().__init__()
        # High Strength
        self.strength_p = 0.49
        self.defense_p = 0.17
        self.health_points_p = 0.17
        self.dexterity_p = 0.17
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        # Validate role and return appropriate action
        if your_role == "attacker":
            self.add_feedback("Random attack")
            return random.choice(["attack", "big_attack", "multiattack", "precise_attack"])
        elif your_role == "defender":
            self.add_feedback("random defense")
            return random.choice(["defend", "dodge", "brace"])
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )

class HighDefenseRandomMoves(Player):
    """Uses random moves"""

    def __init__(self):
        super().__init__()
        # High Defense
        self.strength_p = 0.17
        self.defense_p = 0.49
        self.health_points_p = 0.17
        self.dexterity_p = 0.17
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        # Validate role and return appropriate action
        if your_role == "attacker":
            self.add_feedback("Random attack")
            return random.choice(["attack", "big_attack", "multiattack", "precise_attack"])
        elif your_role == "defender":
            self.add_feedback("random defense")
            return random.choice(["defend", "dodge", "brace"])
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class HighHealthPointsRandomMoves(Player):
    """Makes purely random combat decisions - High health_points build"""

    def __init__(self):
        super().__init__()
        # High Health Points
        self.strength_p = 0.17
        self.defense_p = 0.17
        self.health_points_p = 0.49
        self.dexterity_p = 0.17
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        # Validate role and return appropriate action
        if your_role == "attacker":
            self.add_feedback("Random attack")
            return random.choice(["attack", "big_attack", "multiattack", "precise_attack"])
        elif your_role == "defender":
            self.add_feedback("random defense")
            return random.choice(["defend", "dodge", "brace"])
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class HighDexterityRandomMoves(Player):
    """Uses random moves"""

    def __init__(self):
        super().__init__()
        # High Dexterity
        self.strength_p = 0.17
        self.defense_p = 0.17
        self.health_points_p = 0.17
        self.dexterity_p = 0.49
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        # Validate role and return appropriate action
        if your_role == "attacker":
            self.add_feedback("Random attack")
            return random.choice(["attack", "big_attack", "multiattack", "precise_attack"])
        elif your_role == "defender":
            self.add_feedback("random defense")
            return random.choice(["defend", "dodge", "brace"])
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )

class LowStrengthRandomMoves(Player):
    """Uses random moves"""

    def __init__(self):
        super().__init__()
        # Low Strength
        self.strength_p = 0.05
        self.defense_p = 0.32
        self.health_points_p = 0.31
        self.dexterity_p = 0.32
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        # Validate role and return appropriate action
        if your_role == "attacker":
            self.add_feedback("Random attack")
            return random.choice(["attack", "big_attack", "multiattack", "precise_attack"])
        elif your_role == "defender":
            self.add_feedback("random defense")
            return random.choice(["defend", "dodge", "brace"])
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )

class LowDefenseRandomMoves(Player):
    """Uses random moves"""

    def __init__(self):
        super().__init__()
        # Low Defense
        self.strength_p = 0.32
        self.defense_p = 0.05
        self.health_points_p = 0.31
        self.dexterity_p = 0.32
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        # Validate role and return appropriate action
        if your_role == "attacker":
            self.add_feedback("Random attack")
            return random.choice(["attack", "big_attack", "multiattack", "precise_attack"])
        elif your_role == "defender":
            self.add_feedback("random defense")
            return random.choice(["defend", "dodge", "brace"])
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class LowHealthPointsRandomMoves(Player):
    """Uses random moves"""

    def __init__(self):
        super().__init__()
        # Low Health Points
        self.strength_p = 0.32
        self.defense_p = 0.32
        self.health_points_p = 0.05
        self.dexterity_p = 0.31
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        # Validate role and return appropriate action
        if your_role == "attacker":
            self.add_feedback("Random attack")
            return random.choice(["attack", "big_attack", "multiattack", "precise_attack"])
        elif your_role == "defender":
            self.add_feedback("random defense")
            return random.choice(["defend", "dodge", "brace"])
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class LowDexterityRandomMoves(Player):
    """Uses random moves"""

    def __init__(self):
        super().__init__()
        # Low Strength
        self.strength_p = 0.32
        self.defense_p = 0.32
        self.health_points_p = 0.31
        self.dexterity_p = 0.05
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        # Validate role and return appropriate action
        if your_role == "attacker":
            self.add_feedback("Random attack")
            return random.choice(["attack", "big_attack", "multiattack", "precise_attack"])
        elif your_role == "defender":
            self.add_feedback("random defense")
            return random.choice(["defend", "dodge", "brace"])
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )

class EqualStatsRandomMoves(Player):
    """Uses random moves"""

    def __init__(self):
        super().__init__()
        # Equal Stats
        self.strength_p = 0.25
        self.defense_p = 0.25
        self.health_points_p = 0.25
        self.dexterity_p = 0.25
        self.set_to_original_stats()

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        # Validate role and return appropriate action
        if your_role == "attacker":
            self.add_feedback("Random attack")
            return random.choice(["attack", "big_attack", "multiattack", "precise_attack"])
        elif your_role == "defender":
            self.add_feedback("random defense")
            return random.choice(["defend", "dodge", "brace"])
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )

# List of players to be used for validation games
players = [
    NormalAttackNormalDefend(),
    BigAttackNormalDefend(),
    MultiattackNormalDefend(),
    PreciseAttackNormalDefend(),
    NormalAttackDodge(),
    BigAttackDodge(),
    MultiattackDodge(),
    PreciseAttackDodge(),
    NormalAttackBrace(),
    BigAttackBrace(),
    MultiattackBrace(),
    PreciseAttackBrace(),
    AdaptivePlayer(),
    HighStrengthRandomMoves(),
    HighDefenseRandomMoves(),
    HighHealthPointsRandomMoves(),
    HighDexterityRandomMoves(),
    LowStrengthRandomMoves(),
    LowDefenseRandomMoves(),
    LowHealthPointsRandomMoves(),
    LowDexterityRandomMoves(),
    EqualStatsRandomMoves(),
]
