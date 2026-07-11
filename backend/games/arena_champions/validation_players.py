from typing import Dict
import random

from backend.games.arena_champions.player import Player


class AttackDefend(Player):
    """Uses attack and defend"""

    strategy = (
        "Balanced stats; always uses attack when attacking and defend "
        "when defending."
    )

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
            return "attack"
        elif your_role == "defender":
            return "defend"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class AttackDodge(Player):
    """Uses attack and dodge"""

    strategy = (
        "Balanced stats; always uses attack when attacking and dodge "
        "when defending."
    )

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
            return "attack"
        elif your_role == "defender":
            return "dodge"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class AttackBrace(Player):
    """Uses attack and brace"""

    strategy = (
        "Balanced stats; always uses attack when attacking and brace "
        "when defending."
    )

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
            return "attack"
        elif your_role == "defender":
            return "brace"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class BigAttackDefend(Player):
    """Uses big_attack and defend"""

    strategy = (
        "Balanced stats; always uses big_attack when attacking and defend "
        "when defending."
    )

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
            return "big_attack"
        elif your_role == "defender":
            return "defend"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class BigAttackDodge(Player):
    """Uses big_attack and dodge"""

    strategy = (
        "Balanced stats; always uses big_attack when attacking and dodge "
        "when defending."
    )

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
            return "big_attack"
        elif your_role == "defender":
            return "dodge"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class BigAttackBrace(Player):
    """Uses big_attack and brace"""

    strategy = (
        "Balanced stats; always uses big_attack when attacking and brace "
        "when defending."
    )

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
            return "big_attack"
        elif your_role == "defender":
            return "brace"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class PreciseAttackDefend(Player):
    """Uses precise_attack and defend"""

    strategy = (
        "Balanced stats; always uses precise_attack when attacking and "
        "defend when defending."
    )

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
            return "precise_attack"
        elif your_role == "defender":
            return "defend"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class PreciseAttackDodge(Player):
    """Uses precise_attack and dodge"""

    strategy = (
        "Balanced stats; always uses precise_attack when attacking and "
        "dodge when defending."
    )

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
            return "precise_attack"
        elif your_role == "defender":
            return "dodge"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class PreciseAttackBrace(Player):
    """Uses precise_attack and brace"""

    strategy = (
        "Balanced stats; always uses precise_attack when attacking and "
        "brace when defending."
    )

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
            return "precise_attack"
        elif your_role == "defender":
            return "brace"
        else:
            raise ValueError(
                f"Invalid role: {your_role}. Must be 'attacker' or 'defender'"
            )


class AdaptiveAttacker(Player):
    """Adaptive on attack, standard on defense.

    - When attacking: mirror FullyAdaptivePlayer's attack logic by exploiting the
      opponent's last seen defense using the RPS mapping:
        defend -> big_attack, brace -> precise_attack, dodge -> attack
    - When defending: use a simple default 'defend' strategy (no adaptation).
    """

    strategy = (
        "Exploits the opponent's last seen defence when attacking "
        "(defend → big_attack, brace → precise_attack, dodge → attack); "
        "always defends when defending."
    )

    def __init__(self):
        super().__init__()
        # Balanced default build
        self.attack_proportion = 0.25
        self.defense_proportion = 0.25
        self.dexterity_proportion = 0.25
        self.max_health_proportion = 0.25
        self.set_to_original_stats()

        # Track only the opponent's last defense (that's all we need for attack)
        self.last_seen_opponent_defense = None
        self._defense_actions = {"defend", "dodge", "brace"}
        self._best_attack_vs_defense = {
            "defend": "big_attack",
            "brace": "precise_attack",
            "dodge": "attack",
        }

    def _remember(self, last_opponent_action: str):
        if last_opponent_action and last_opponent_action in self._defense_actions:
            self.last_seen_opponent_defense = last_opponent_action

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        # Remember last defense to exploit on our attack
        self._remember(last_opponent_action)

        if your_role == "attacker":
            if (
                self.last_seen_opponent_defense
                and self.last_seen_opponent_defense in self._best_attack_vs_defense
            ):
                chosen = self._best_attack_vs_defense[self.last_seen_opponent_defense]
                # Avoid risky big_attack if we're low HP
                if chosen == "big_attack" and self.health < 0.3 * self.max_health:
                    chosen = "attack"
                return chosen
            return "precise_attack"

        if your_role == "defender":
            return "defend"

        raise ValueError(f"Invalid role: {your_role}. Must be 'attacker' or 'defender'")


class FullyAdaptivePlayer(Player):
    """Fully adaptive: counters last seen attack when defending and exploits last seen defense when attacking.

    - Defense picks the strong response to the opponent's last attack:
        attack -> brace, big_attack -> dodge, precise_attack -> defend
    - Attack picks the strong move vs opponent's last defense:
        defend -> big_attack, brace -> precise_attack, dodge -> attack
    """

    strategy = (
        "Fully adaptive: counters the opponent's last seen attack when "
        "defending and exploits their last seen defence when attacking."
    )

    def __init__(self):
        super().__init__()
        # Balanced baseline build
        self.attack_proportion = 0.25
        self.defense_proportion = 0.25
        self.dexterity_proportion = 0.25
        self.max_health_proportion = 0.25
        self.set_to_original_stats()

        # Memory of opponent tendencies
        self.last_seen_opponent_attack = None
        self.last_seen_opponent_defense = None

        # RPS maps
        self._attack_actions = {"attack", "big_attack", "precise_attack"}
        self._defense_actions = {"defend", "dodge", "brace"}
        self._best_defense_vs_attack = {
            "attack": "brace",
            "big_attack": "dodge",
            "precise_attack": "defend",
        }
        self._best_attack_vs_defense = {
            "defend": "big_attack",
            "brace": "precise_attack",
            "dodge": "attack",
        }

    def _remember(self, last_opponent_action: str):
        if not last_opponent_action:
            return
        if last_opponent_action in self._attack_actions:
            self.last_seen_opponent_attack = last_opponent_action
        elif last_opponent_action in self._defense_actions:
            self.last_seen_opponent_defense = last_opponent_action

    def make_combat_decision(
        self,
        opponent_stats: Dict,
        turn: int,
        your_role: str,
        last_opponent_action: str = None,
    ) -> str:
        # Update memory from whatever the opponent last did
        self._remember(last_opponent_action)

        if your_role == "attacker":
            # Exploit the last defense we observed
            if self.last_seen_opponent_defense in self._best_attack_vs_defense:
                chosen = self._best_attack_vs_defense[self.last_seen_opponent_defense]
                # Optional: avoid risky big_attack at low HP
                if chosen == "big_attack" and self.health < 0.3 * self.max_health:
                    chosen = "attack"
                return chosen

            return "precise_attack"

        if your_role == "defender":
            # Counter the last attack we observed
            if self.last_seen_opponent_attack in self._best_defense_vs_attack:
                chosen = self._best_defense_vs_attack[self.last_seen_opponent_attack]
                return chosen
            return "defend"

        raise ValueError(f"Invalid role: {your_role}. Must be 'attacker' or 'defender'")


class OptimisedRandomVCC(Player):
    strategy = (
        "Attack-heavy build; picks randomly between attack and "
        "precise_attack when attacking, and brace or dodge when defending."
    )

    def __init__(self):
        super().__init__()
        # Distribute proportions between 0.2 and 0.4 and keep the sum <= 1.0
        self.attack_proportion = 0.3
        self.defense_proportion = 0.2
        self.max_health_proportion = 0.3
        self.dexterity_proportion = 0.2
        self.set_to_original_stats()
        # This is an easy way of tracking opponent actions
        self.opponent_last_attack = "" 
        self.opponent_last_defense = ""

    
    def make_combat_decision(self, opponent_stats, turn, your_role, last_opponent_action=None):
        # ROLE-BASED COMBAT: You are told if you're attacking or defending
        # your_role will be either "attacker" or "defender"
        # ------------------------------------------------------------------------------------
        # USEFUL INFORMATION ABOUT THE GAME AND YOUR OPPONENT:
        self.add_feedback(opponent_stats)
        opponent_action= "Here are the opponents last action: " + str(last_opponent_action)
        self.add_feedback(opponent_action)
        # NOTE: self.add_feedback needs a string or a dictionary
        #-------------------------------------------------------------------------------------
        # Chose a random valid attack
        if your_role == "attacker":
            return random.choice(['attack', 'precise_attack'])

        # Always brace as defender        
        elif your_role == "defender":
            return random.choice(['brace', 'dodge'])


class StrategicAdaptiveRandom(Player):
    strategy = (
        "Attack-heavy build; big_attacks weakened opponents, counters the "
        "opponent's last observed moves, and falls back to random choices."
    )

    def __init__(self):
        super().__init__()
        # Distribute proportions between 0.2 and 0.4 and keep the sum <= 1.0
        self.attack_proportion = 0.3
        self.defense_proportion = 0.2
        self.max_health_proportion = 0.3
        self.dexterity_proportion = 0.2
        self.set_to_original_stats()
        # This is an easy way of tracking opponent actions
        self.opponent_last_attack = "" 
        self.opponent_last_defense = ""

    
    def make_combat_decision(self, opponent_stats, turn, your_role, last_opponent_action=None):
        # ROLE-BASED COMBAT: You are told if you're attacking or defending
        # your_role will be either "attacker" or "defender"
        # ------------------------------------------------------------------------------------
        # USEFUL INFORMATION ABOUT THE GAME AND YOUR OPPONENT:
        self.add_feedback(opponent_stats)
        opponent_action= "Here are the opponents last action: " + str(last_opponent_action)
        self.add_feedback(opponent_action)
        # NOTE: self.add_feedback needs a string or a dictionary
        #-------------------------------------------------------------------------------------

        # Chose a random valid attack
        if your_role == "attacker":
            if opponent_stats["health"] < 90 and self.health > 30:
                return "big_attack"
            # Adaptive action (last_opponent_action is None on the first turn)
            self.opponent_last_attack = last_opponent_action or ""
            self.add_feedback("opponents last defense: "+ self.opponent_last_defense)
            if self.opponent_last_defense == "brace": return "precise_attack"
            if self.opponent_last_defense == "dodge": return "attack"
            if self.opponent_last_defense == "defend" and self.health >30: return "big_attack"
            return random.choice(['attack', 'precise_attack'])

        # Always brace as defender
        elif your_role == "defender":
            if self.health <25: return "dodge"
            self.opponent_last_defense = last_opponent_action or ""
            if self.opponent_last_attack == "attack": return "brace"
            if self.opponent_last_attack == "big_attack": return "dodge"
            if self.opponent_last_attack == "precise_attack": return "defend"
            return random.choice(['brace', 'dodge'])


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
    AdaptiveAttacker(),
    FullyAdaptivePlayer(),
    OptimisedRandomVCC(),
    StrategicAdaptiveRandom(),
]