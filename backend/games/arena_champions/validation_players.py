import random
from typing import Dict

from backend.games.arena_champions.player import Player


class GlassCannon(Player):
    """High attack, low defense/HP build"""

    def __init__(self):
        super().__init__()
        self.attack = 50  # Max attack
        self.defense = 10
        self.health = 20
        self.dexterity = 20

    def make_combat_decision(self, combat_state: Dict) -> str:
        # Aggressive strategy - focus on big attacks when opponent is weak
        hp_percentage = combat_state['my_current_hp'] / combat_state['my_max_hp']

        # If we're very low on health, try to run away
        if hp_percentage < 0.2:
            self.add_feedback("Very low HP - running away!")
            return "run_away"

        # Use big attack when opponent is low (if we can see their HP)
        if combat_state.get('opponent_stats'):
            opp_hp_percent = combat_state['opponent_stats']['current_hp'] / combat_state['opponent_stats']['hp']
            if opp_hp_percent < 0.4 and hp_percentage > 0.5:
                self.add_feedback("Opponent low - big attack!")
                return "big_attack"

        # Default to normal attack
        return 'attack'


class DodgeMaster(Player):
    """High dexterity build focused on avoiding damage"""

    def __init__(self):
        super().__init__()
        self.attack = 25
        self.defense = 10
        self.health = 15
        self.dexterity = 50  # Max dexterity

    def make_combat_decision(self, combat_state: Dict) -> str:
        hp_percentage = combat_state["my_current_hp"] / combat_state["my_max_hp"]

        # Run away if very low health
        if hp_percentage < 0.15:
            self.add_feedback("Critical health - running!")
            return "run_away"

        # Always try to dodge when opponent might attack
        if combat_state.get("last_opponent_action") in ["big_attack", "attack"]:
            self.add_feedback("Trying to dodge incoming attack")
            return "dodge"

        # Counter-attack when safe
        if hp_percentage > 0.6:
            return "attack"
        else:
            return "dodge"


class Tank(Player):
    """High HP and defense, focused on outlasting opponents"""

    def __init__(self):
        super().__init__()
        self.attack = 15
        self.defense = 35
        self.health = 45
        self.dexterity = 5

    def make_combat_decision(self, combat_state: Dict) -> str:
        hp_percentage = combat_state["my_current_hp"] / combat_state["my_max_hp"]

        # Only run if absolutely desperate
        if hp_percentage < 0.1:
            self.add_feedback("Desperate retreat!")
            return "run_away"

        # Defend when under attack
        if combat_state.get("last_opponent_action") in ["big_attack", "attack"]:
            self.add_feedback("Defending against attack")
            return 'defend'

        # Attack when we have health advantage
        if combat_state.get("opponent_stats"):
            my_hp_percent = hp_percentage
            opp_hp_percent = (
                combat_state["opponent_stats"]["current_hp"]
                / combat_state["opponent_stats"]["hp"]
            )

            if my_hp_percent > opp_hp_percent * 1.5:
                self.add_feedback("Health advantage - attacking!")
                return "attack"

        # Default to defense
        return "defend"


class Berserker(Player):
    """Aggressive build that uses big attacks frequently"""

    def __init__(self):
        super().__init__()
        self.attack = 40
        self.defense = 20
        self.health = 30
        self.dexterity = 10

    def make_combat_decision(self, combat_state: Dict) -> str:
        hp_percentage = combat_state["my_current_hp"] / combat_state["my_max_hp"]
        turn = combat_state["turns_elapsed"]

        # Run away only when critically low
        if hp_percentage < 0.2:
            self.add_feedback("Low health - tactical retreat")
            return "run_away"

        # Use big attack early in fight when we have health
        if hp_percentage > 0.6 and turn <= 3:
            self.add_feedback("Early big attack!")
            return "big_attack"

        # Try to finish with big attack if opponent seems weak
        if combat_state.get("opponent_stats"):
            opp_hp_percent = (
                combat_state["opponent_stats"]["current_hp"]
                / combat_state["opponent_stats"]["hp"]
            )
            if opp_hp_percent < 0.3 and hp_percentage > 0.4:
                self.add_feedback("Finishing move!")
                return "big_attack"

        # Defend when badly hurt
        if hp_percentage < 0.4:
            return 'defend'

        # Default attack
        return 'attack'


class Balanced(Player):
    """Well-rounded build with adaptive strategy"""

    def __init__(self):
        super().__init__()
        self.attack = 25
        self.defense = 25
        self.health = 25
        self.dexterity = 25

    def make_combat_decision(self, combat_state: Dict) -> str:
        hp_percentage = combat_state["my_current_hp"] / combat_state["my_max_hp"]

        # Emergency escape
        if hp_percentage < 0.2:
            self.add_feedback("Emergency retreat!")
            return "run_away"

        # Adapt based on opponent info
        if combat_state.get("opponent_stats"):
            opp_stats = combat_state["opponent_stats"]
            opp_hp_percent = opp_stats["current_hp"] / opp_stats["hp"]

            # If opponent is almost dead, finish them
            if opp_hp_percent < 0.2:
                self.add_feedback("Finishing weak opponent")
                return "attack"

            # If opponent has high attack, focus on defense
            if opp_stats["attack"] > 35:
                self.add_feedback("High-attack opponent - defending")
                return "defend"

            # If opponent has low dexterity but high defense, use big attack
            if opp_stats["dexterity"] < 15 and opp_stats["defense"] > 30:
                if hp_percentage > 0.5:
                    self.add_feedback("Slow tank - big attack!")
                    return "big_attack"

        # Default balanced approach
        if hp_percentage > 0.6:
            return "attack"
        elif hp_percentage < 0.4:
            return "defend"
        else:
            # Alternate between dodge and defend
            turn = combat_state["turns_elapsed"]
            return "dodge" if turn % 2 == 0 else "defend"


class Coward(Player):
    """Survival-focused player that runs away often"""

    def __init__(self):
        super().__init__()
        self.attack = 20
        self.defense = 30
        self.health = 40
        self.dexterity = 10

    def make_combat_decision(self, combat_state: Dict) -> str:
        hp_percentage = combat_state['my_current_hp'] / combat_state['my_max_hp']

        # Run away frequently
        if hp_percentage < 0.5:
            self.add_feedback("Running away - safety first!")
            return "run_away"

        # Only attack when very healthy and opponent seems weak
        if combat_state.get('opponent_stats'):
            opp_hp_percent = combat_state['opponent_stats']['current_hp'] / combat_state['opponent_stats']['hp']
            if hp_percentage > 0.8 and opp_hp_percent < 0.3:
                self.add_feedback("Safe to attack now")
                return "attack"

        # Default to defense
        self.add_feedback("Playing it safe")
        return "defend"


# List of players to be used for validation games
players = [
    GlassCannon(),
    DodgeMaster(),
    Tank(),
    Berserker(),
    Balanced(),
    Coward(),
]
