from typing import Dict
import random

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

class MultiattackNormalDefend(Player):
    """Always uses multiattack and defend"""

    def __init__(self):
        super().__init__()
        # Higher dexterity and defence to take advantage of its moves, high strength, low vitality 
        self.strength = 25
        self.defense = 30
        self.vitality = 10
        self.dexterity = 35
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
        # High dexterity to use precise attack well, moderate defense and attack, low vitality
        self.strength = 25
        self.defense = 25
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
        
class MultiattackDodge(Player):
    """Always uses multiattack and dodge"""

    def __init__(self):
        super().__init__()
        # high dexterity and attack to combo into really high damage, low non-dexterity defensive stats
        self.strength = 40
        self.defense = 5
        self.vitality = 10
        self.dexterity = 45
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
        #high dexterity for dodging and precise attack, moderate vitality, low other stats
        self.strength = 15
        self.defense = 5
        self.vitality = 30
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
        # vitality and defense are less important, and dexterity is useless when the attacks/defenses you use don't require it. 
        self.strength = 50
        self.defense = 20
        self.vitality = 25
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
        # Max strength to take advantage of big attack. Defense, vitality, and dexterity don't matter much
        self.strength = 50
        self.defense = 24
        self.vitality = 21
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
        # very high dexterity and attack, low defensive stats
        self.strength = 40
        self.defense = 10
        self.vitality = 15
        self.dexterity = 35
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
        self.strength = 40
        self.defense = 15
        self.vitality = 15
        self.dexterity = 30
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
        self.strength = 49
        self.defense = 17
        self.vitality = 17
        self.dexterity = 17
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
        self.strength = 17
        self.defense = 49
        self.vitality = 17
        self.dexterity = 17
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
            self.add_feedback("Random attack")
            return random.choice(["attack", "big_attack", "multiattack", "precise_attack"])
        elif your_role == "defender":
            self.add_feedback("random defense")
            return random.choice(["defend", "dodge", "brace"])
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )

class HighVitalityRandomMoves(Player):
    """Uses random moves"""

    def __init__(self):
        super().__init__()
        # High Vitality
        self.strength = 17
        self.defense = 17
        self.vitality = 49
        self.dexterity = 17
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
        self.strength = 17
        self.defense = 17
        self.vitality = 17
        self.dexterity = 49
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
        self.strength = 5
        self.defense = 32
        self.vitality = 31
        self.dexterity = 32
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
        self.strength = 32
        self.defense = 5
        self.vitality = 31
        self.dexterity = 32
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
            self.add_feedback("Random attack")
            return random.choice(["attack", "big_attack", "multiattack", "precise_attack"])
        elif your_role == "defender":
            self.add_feedback("random defense")
            return random.choice(["defend", "dodge", "brace"])
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )

class LowVitalityRandomMoves(Player):
    """Uses random moves"""

    def __init__(self):
        super().__init__()
        # Low Vitality
        self.strength = 32
        self.defense = 32
        self.vitality = 5
        self.dexterity = 31
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
        self.strength = 32
        self.defense = 32
        self.vitality = 31
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
        self.strength = 25
        self.defense = 25
        self.vitality = 25
        self.dexterity = 25
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
    HighVitalityRandomMoves(),
    HighDexterityRandomMoves(),
    LowStrengthRandomMoves(),
    LowDefenseRandomMoves(),
    LowVitalityRandomMoves(),
    LowDexterityRandomMoves(),
    EqualStatsRandomMoves()
]
