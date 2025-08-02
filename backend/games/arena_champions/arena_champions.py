import json
import random
from typing import Dict, List, Optional, Tuple

from backend.games.base_game import BaseGame


class ArenaChampionsGame(BaseGame):
    starter_code = """
from games.arena_champions.player import Player
import random

class CustomPlayer(Player):
    def __init__(self):
        super().__init__()
        # Set your character attributes (each must be between 5 and 50)
        self.attack = 30      # Damage per hit
        self.defense = 20     # Damage reduction %
        self.health = 25      # Health points
        self.dexterity = 25   # Dodge chance %
        
        # Example builds:
        # Glass Cannon: attack=45, defense=5, health=25, dexterity=25
        # Tank: attack=10, defense=40, health=45, dexterity=5
        # Dodger: attack=25, defense=10, health=15, dexterity=50
    
    def make_combat_decision(self, combat_state):
        # Available actions:
        # Attack: 'attack' (normal damage), 'big_attack' (2x damage, lose 50% health)
        # Defense: 'defend' (reduce damage), 'dodge' (chance to avoid all damage), 
        #          'run_away' (lose 50% health, no damage)
        
        # Combat state info:
        # - my_current_hp, my_max_hp, my_attack, my_defense, my_dexterity
        # - opponent_stats (if has_preview): attack, defense, hp, current_hp, dexterity
        # - turns_elapsed, last_opponent_action, my_status, has_preview
        
        hp_percentage = combat_state['my_current_hp'] / combat_state['my_max_hp']
        
        # Example strategy
        if hp_percentage < 0.2:
            self.add_feedback("Low health - running away!")
            return 'run_away'
        elif hp_percentage < 0.4:
            self.add_feedback("Defending to stay alive")
            return 'defend'
        elif combat_state.get('opponent_stats'):
            opp_hp = combat_state['opponent_stats']['current_hp']
            if opp_hp < 20 and hp_percentage > 0.5:
                self.add_feedback("Finishing with big attack!")
                return 'big_attack'
        
        self.add_feedback("Standard attack")
        return 'attack'
"""

    game_instructions = """
# Arena Champions - Enhanced Combat Programming Game

Design a champion that battles others in 1-on-1 combat through strategic programming.

## Character Creation
- Set your attributes directly in the `__init__` method
- Each attribute must be between **5 and 50**:
  - **attack**: Damage per strike
  - **defense**: Damage reduction percentage (capped at 90% effectiveness)
  - **health**: Total health points
  - **dexterity**: Dodge chance percentage

## Combat Actions

### Attack Actions:
- **attack**: Deal normal damage based on your attack stat
- **big_attack**: Deal double damage but lose 50% of your current health

### Defense Actions:
- **defend**: Reduce incoming damage by your defense percentage
- **dodge**: Attempt to completely avoid damage (dexterity% chance of success)
- **run_away**: Lose 50% of current health but take no damage this turn and avoid all future attacks

## Combat Mechanics
- **Damage Calculation**: Base damage = attacker's attack stat
- **Defense**: Reduces damage by defense% (capped at 90% damage reduction)
- **Dodge**: dexterity% chance to completely avoid all damage
- **Big Attack Cost**: Lose 50% of current HP when using big_attack
- **Running Away**: Lose 50% current HP, but become immune to further damage

## Preview System
- Each pair fights twice with alternating information advantage
- One player gets full opponent stats in first match
- Roles reverse in rematch
- Use this information to adapt your strategy!

## Programming Challenge
Implement:
1. `__init__()`: Set your character attributes (attack, defense, health, dexterity) between 5-50
2. `make_combat_decision()`: Make tactical decisions each turn

## Leveling Up
- **Each win automatically adds +1 to ALL attributes**
- Plan your initial build knowing you'll become stronger with victories

## Strategy Tips
- **High Attack**: Deal more damage but consider survivability
- **High Defense**: Consistent damage reduction, good for tanking
- **High Dexterity**: High-risk/high-reward - either dodge completely or take full damage
- **High Health**: More staying power, especially important for big_attack users
- **Big Attacks**: High damage but risky - time them carefully
- **Running Away**: Sometimes retreating is better than dying
- **Preview Info**: Use opponent stats to counter their build

## Example Builds
- **Glass Cannon**: attack=45, defense=5, health=25, dexterity=25
- **Tank**: attack=10, defense=40, health=45, dexterity=5  
- **Dodge Master**: attack=25, defense=10, health=15, dexterity=50
- **Balanced**: attack=25, defense=25, health=25, dexterity=25
"""

    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        self.battle_history = {}  # Stores battle outcomes
        self.game_feedback = {"game": "arena_champions", "battles": []}
        self.initialize_characters()

    def initialize_characters(self, validate_initial_attributes=True):
        """Initialize all characters using their attribute settings"""
        for player in self.players:
            player_name = str(player.name)

            # Store original attribute values for reset purposes (only once)
            if not hasattr(player, "_original_attributes"):
                player._original_attributes = {
                    "attack": player.attack,
                    "defense": player.defense,
                    "health": player.health,
                    "dexterity": player.dexterity,
                }

            # Only validate player attributes at the start of simulation
            if validate_initial_attributes:
                try:
                    self._validate_player_attributes(player)
                except ValueError as e:
                    raise ValueError(f"Player {player_name}: {str(e)}")

            # Add additional attributes needed for the game
            player.max_hp = player.health
            player.current_hp = player.health

            # Only initialize wins/losses if they don't exist (preserve during gameplay)
            if not hasattr(player, "wins"):
                player.wins = 0
            if not hasattr(player, "losses"):
                player.losses = 0

            self.battle_history[player_name] = []

    def _validate_player_attributes(self, player):
        """Validate that player attributes are within allowed ranges (only for initial setup)"""
        attributes = ["attack", "defense", "health", "dexterity"]

        for attr_name in attributes:
            if not hasattr(player, attr_name):
                raise ValueError(f"Missing required attribute: {attr_name}")

            value = getattr(player, attr_name)
            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Attribute {attr_name} must be a number, got {type(value).__name__}"
                )

            if value < 5 or value > 50:
                raise ValueError(
                    f"Initial attribute {attr_name} must be between 5 and 50, got {value}"
                )

    def _validate_distribution(self, distribution: Dict, total_points: int) -> bool:
        """Legacy method - no longer used"""
        return True

    def calculate_damage(self, attacker, defender, attack_type: str = "normal") -> int:
        """Calculate damage based on attack type"""
        base_damage = attacker.attack

        if attack_type == "big_attack":
            base_damage *= 2

        return max(1, int(base_damage))

    def apply_defense(
        self, damage: int, defender, defense_action: str
    ) -> Tuple[int, bool, str]:
        """Apply defense and return (final_damage, dodged, defense_message)"""
        if defense_action == "run_away":
            return 0, False, "ran away"

        if defense_action == "dodge":
            # Try to dodge (cap at 100% chance regardless of actual dexterity stat)
            dodge_chance = min(defender.dexterity, 100)
            if random.randint(1, 100) <= dodge_chance:
                return 0, True, "dodged completely"
            else:
                # Failed to dodge, take full damage
                return damage, False, "dodge failed"

        if defense_action == "defend":
            # Apply defense reduction (cap at 90% effectiveness regardless of actual defense stat)
            defense_reduction = min(defender.defense, 90) / 100  # Cap at 90%
            damage = int(damage * (1 - defense_reduction))
            defense_message = f"defended (reduced by {min(defender.defense, 90)}%)"
            return max(1, damage), False, defense_message

        # No defense action, take full damage
        return damage, False, "no defense"

    def execute_combat(self, player1, player2, player1_has_preview: bool) -> Tuple[str, Dict]:
        """Execute a single combat between two players"""
        p1_name = str(player1.name)
        p2_name = str(player2.name)

        # Reset current HP to max for battle
        player1.current_hp = player1.max_hp
        player2.current_hp = player2.max_hp

        # Battle state
        battle_log = {
            'player1': p1_name,
            'player2': p2_name,
            'player1_has_preview': player1_has_preview,
            'turns': [],
            'winner': None
        }

        # Status effects
        p1_status = 'normal'
        p2_status = 'normal'
        p1_ran_away = False
        p2_ran_away = False

        turn = 0
        last_p1_action = None
        last_p2_action = None

        while player1.current_hp > 0 and player2.current_hp > 0 and turn < 100:
            turn += 1
            turn_data = {"turn": turn, "actions": {}, "results": {}}

            # Player 1 turn
            if not p1_ran_away:
                combat_state = self._create_combat_state(
                    player1,
                    player2 if player1_has_preview else None,
                    turn,
                    last_p2_action,
                    p1_status,
                    True,
                )

                try:
                    p1_action = player1.make_combat_decision(combat_state)
                    if p1_action not in [
                        "attack",
                        "big_attack",
                        "defend",
                        "dodge",
                        "run_away",
                    ]:
                        p1_action = 'attack'
                except Exception as e:
                    self.add_feedback(f"Error in {p1_name} combat decision: {e}")
                    p1_action = 'attack'

                turn_data['actions'][p1_name] = p1_action
                last_p1_action = p1_action

                if p1_action == "run_away":
                    p1_ran_away = True
                    player1.current_hp = max(1, player1.current_hp // 2)
                    turn_data["results"][f"{p1_name}_ran_away"] = True
            else:
                turn_data["actions"][p1_name] = "ran_away (continuing)"

            # Player 2 turn
            if not p2_ran_away:
                combat_state = self._create_combat_state(
                    player2,
                    player1 if not player1_has_preview else None,
                    turn,
                    last_p1_action,
                    p2_status,
                    False,
                )

                try:
                    p2_action = player2.make_combat_decision(combat_state)
                    if p2_action not in [
                        "attack",
                        "big_attack",
                        "defend",
                        "dodge",
                        "run_away",
                    ]:
                        p2_action = 'attack'
                except Exception as e:
                    self.add_feedback(f"Error in {p2_name} combat decision: {e}")
                    p2_action = 'attack'

                turn_data['actions'][p2_name] = p2_action
                last_p2_action = p2_action

                if p2_action == "run_away":
                    p2_ran_away = True
                    player2.current_hp = max(1, player2.current_hp // 2)
                    turn_data["results"][f"{p2_name}_ran_away"] = True
            else:
                turn_data["actions"][p2_name] = "ran_away (continuing)"

            # Resolve combat if both players are still fighting
            if not p1_ran_away and not p2_ran_away:
                # Player 1 attacks Player 2 (only if P1 isn't doing defensive action)
                if p1_action in ["attack", "big_attack"]:
                    damage = self.calculate_damage(player1, player2, p1_action)
                    final_damage, dodged, defense_msg = self.apply_defense(
                        damage, player2, p2_action
                    )

                    if not dodged:
                        player2.current_hp -= final_damage

                    turn_data["results"][f"{p1_name}_damage_dealt"] = (
                        final_damage if not dodged else 0
                    )
                    turn_data["results"][f"{p2_name}_defense_result"] = defense_msg

                    # Apply big attack health cost
                    if p1_action == "big_attack":
                        health_cost = player1.current_hp // 2
                        player1.current_hp -= health_cost
                        turn_data["results"][f"{p1_name}_health_cost"] = health_cost

                # Player 2 attacks Player 1 (only if P2 isn't doing defensive action)
                if p2_action in ["attack", "big_attack"]:
                    damage = self.calculate_damage(player2, player1, p2_action)
                    final_damage, dodged, defense_msg = self.apply_defense(
                        damage, player1, p1_action
                    )

                    if not dodged:
                        player1.current_hp -= final_damage

                    turn_data["results"][f"{p2_name}_damage_dealt"] = (
                        final_damage if not dodged else 0
                    )
                    turn_data["results"][f"{p1_name}_defense_result"] = defense_msg

                    # Apply big attack health cost
                    if p2_action == "big_attack":
                        health_cost = player2.current_hp // 2
                        player2.current_hp -= health_cost
                        turn_data["results"][f"{p2_name}_health_cost"] = health_cost
            elif not p1_ran_away and p2_ran_away:
                # Only P1 can attack since P2 ran away
                if p1_action in ["attack", "big_attack"]:
                    # P2 takes no damage since they ran away
                    turn_data["results"][f"{p1_name}_damage_dealt"] = 0
                    turn_data["results"][
                        f"{p2_name}_defense_result"
                    ] = "safe (ran away)"

                    # Apply big attack health cost to P1
                    if p1_action == "big_attack":
                        health_cost = player1.current_hp // 2
                        player1.current_hp -= health_cost
                        turn_data["results"][f"{p1_name}_health_cost"] = health_cost
            elif p1_ran_away and not p2_ran_away:
                # Only P2 can attack since P1 ran away
                if p2_action in ["attack", "big_attack"]:
                    # P1 takes no damage since they ran away
                    turn_data["results"][f"{p2_name}_damage_dealt"] = 0
                    turn_data["results"][
                        f"{p1_name}_defense_result"
                    ] = "safe (ran away)"

                    # Apply big attack health cost to P2
                    if p2_action == "big_attack":
                        health_cost = player2.current_hp // 2
                        player2.current_hp -= health_cost
                        turn_data["results"][f"{p2_name}_health_cost"] = health_cost

            # Record HP
            turn_data["hp"] = {
                p1_name: max(0, player1.current_hp),
                p2_name: max(0, player2.current_hp),
            }

            battle_log['turns'].append(turn_data)

            # Add player feedback
            if player1.feedback:
                self.add_player_feedback(player1, turn, p2_name)
            if player2.feedback:
                self.add_player_feedback(player2, turn, p1_name)

            # Check for winner (if both ran away, highest HP wins)
            if p1_ran_away and p2_ran_away:
                if player1.current_hp > player2.current_hp:
                    battle_log["winner"] = p1_name
                    return p1_name, battle_log
                else:
                    battle_log["winner"] = p2_name
                    return p2_name, battle_log

        # Determine winner
        if player1.current_hp > 0:
            battle_log['winner'] = p1_name
            return p1_name, battle_log
        else:
            battle_log['winner'] = p2_name
            return p2_name, battle_log

    def _create_combat_state(
        self,
        my_player,
        opponent_player=None,
        turn: int = 0,
        last_opponent_action: Optional[str] = None,
        my_status: str = "normal",
        has_preview: bool = False,
    ) -> Dict:
        """Create the combat state for a player"""
        state = {
            "my_current_hp": my_player.current_hp,
            "my_max_hp": my_player.max_hp,
            "my_attack": my_player.attack,
            "my_defense": my_player.defense,
            "my_dexterity": my_player.dexterity,
            "turns_elapsed": turn,
            "last_opponent_action": last_opponent_action,
            "my_status": my_status,
            "has_preview": has_preview,
        }

        if opponent_player:
            state["opponent_stats"] = {
                "attack": opponent_player.attack,
                "defense": opponent_player.defense,
                "hp": opponent_player.max_hp,
                "current_hp": opponent_player.current_hp,
                "dexterity": opponent_player.dexterity,
            }

        return state

    def apply_level_up(self, player, player_name: str):
        """Apply level up - add 1 point to all attributes"""
        try:
            # Add 1 to all attributes
            player.attack += 1
            player.defense += 1
            player.dexterity += 1
            hp_increase = 1
            player.health += hp_increase
            player.max_hp += hp_increase

            self.add_feedback(f"{player_name} leveled up: +1 to all attributes")

        except Exception as e:
            self.add_feedback(f"Error applying level up for {player_name}: {e}")

    def play_game(self, custom_rewards=None):
        """Play a complete tournament"""
        self.game_feedback = {"game": "arena_champions", "battles": []}
        # Initialize characters without validation (preserve leveled-up stats)
        self.initialize_characters(validate_initial_attributes=False)

        # Each pair fights twice with alternating preview advantage
        battle_count = 0
        for i, player1 in enumerate(self.players):
            for j, player2 in enumerate(self.players):
                if i != j:
                    battle_count += 1
                    # First battle: player1 has preview
                    winner1, battle_log1 = self.execute_combat(player1, player2, True)
                    self.game_feedback['battles'].append(battle_log1)

                    # Update stats
                    winner_name = winner1
                    loser_name = str(player2.name) if winner1 == str(player1.name) else str(player1.name)
                    winner_player = player1 if winner1 == str(player1.name) else player2
                    loser_player = player2 if winner1 == str(player1.name) else player1
                    winner_player.wins += 1
                    loser_player.losses += 1

                    # Apply level up
                    winner_player = player1 if winner1 == str(player1.name) else player2
                    self.apply_level_up(winner_player, winner_name)

                    # Record battle
                    self.battle_history[str(player1.name)].append({
                        'opponent': str(player2.name),
                        'result': 'win' if winner1 == str(player1.name) else 'loss',
                        'had_preview': True
                    })
                    self.battle_history[str(player2.name)].append({
                        'opponent': str(player1.name),
                        'result': 'win' if winner1 == str(player2.name) else 'loss',
                        'had_preview': False
                    })

                    # Second battle: player2 has preview
                    winner2, battle_log2 = self.execute_combat(player1, player2, False)
                    self.game_feedback['battles'].append(battle_log2)

                    # Update stats
                    winner_name = winner2
                    loser_name = str(player2.name) if winner2 == str(player1.name) else str(player1.name)
                    winner_player = player1 if winner2 == str(player1.name) else player2
                    loser_player = player2 if winner2 == str(player1.name) else player1
                    winner_player.wins += 1
                    loser_player.losses += 1

                    # Apply level up
                    winner_player = player1 if winner2 == str(player1.name) else player2
                    self.apply_level_up(winner_player, winner_name)

                    # Record battle
                    self.battle_history[str(player1.name)].append({
                        'opponent': str(player2.name),
                        'result': 'win' if winner2 == str(player1.name) else 'loss',
                        'had_preview': False
                    })
                    self.battle_history[str(player2.name)].append({
                        'opponent': str(player1.name),
                        'result': 'win' if winner2 == str(player2.name) else 'loss',
                        'had_preview': True
                    })

        # Calculate final scores
        scores = {}
        for player in self.players:
            scores[str(player.name)] = player.wins

        # Additional stats for the table
        total_damage = {}
        for battle in self.game_feedback['battles']:
            for turn in battle['turns']:
                for key, value in turn.get("results", {}).items():
                    if "_damage_dealt" in key:
                        player = key.replace("_damage_dealt", "")
                        total_damage[player] = total_damage.get(player, 0) + value

        # Create final stats dictionary using player attributes
        final_stats = {}
        for player in self.players:
            player_name = str(player.name)
            final_stats[player_name] = {
                "attack": player.attack,
                "defense": player.defense,
                "hp": player.health,
                "dexterity": player.dexterity,
                "max_hp": player.max_hp,
                "current_hp": player.current_hp,
                "wins": player.wins,
                "losses": player.losses,
            }

        return {
            "points": scores,
            "score_aggregate": scores,
            "table": {
                "final_stats": final_stats,
                "total_damage": total_damage,
                "battles_fought": {
                    p: len(self.battle_history[p]) for p in self.battle_history
                },
            },
        }

    def run_simulations(self, num_simulations, league, custom_rewards=None):
        """Run multiple simulations"""
        total_points = {str(player.name): 0 for player in self.players}
        total_wins = {str(player.name): 0 for player in self.players}
        total_damage = {str(player.name): 0 for player in self.players}

        for _ in range(num_simulations):
            self.reset()
            results = self.play_game(custom_rewards)

            for player, points in results['points'].items():
                total_points[str(player)] += points
                total_wins[str(player)] += points  # Since points = wins in this game

            for player, damage in results['table']['total_damage'].items():
                total_damage[str(player)] += damage

        return {
            'total_points': total_points,
            'num_simulations': num_simulations,
            'table': {
                'total_wins': total_wins,
                'total_damage': total_damage,
                'avg_wins_per_sim': {p: total_wins[p] / num_simulations for p in total_wins}
            }
        }

    def reset(self):
        """Reset game state - validate attributes only at start of new simulation"""
        super().reset()
        self.battle_history = {}
        self.game_feedback = {"game": "arena_champions", "battles": []}

        # Reset player attributes to their original values before validation
        for player in self.players:
            if hasattr(player, "_original_attributes"):
                player.attack = player._original_attributes["attack"]
                player.defense = player._original_attributes["defense"]
                player.health = player._original_attributes["health"]
                player.dexterity = player._original_attributes["dexterity"]

                # Reset wins and losses
                player.wins = 0
                player.losses = 0

        # Reset and validate attributes for fresh simulation
        self.initialize_characters(validate_initial_attributes=True)

    def add_player_feedback(self, player, turn, opponent_name):
        """Add feedback from a player for a specific turn"""
        if player.feedback:
            player_name = str(player.name)
            if player_name not in self.player_feedback:
                self.player_feedback[player_name] = []

            self.player_feedback[player_name].append({
                'turn': turn,
                'opponent': opponent_name,
                'messages': list(player.feedback)
            })
            player.feedback = []
