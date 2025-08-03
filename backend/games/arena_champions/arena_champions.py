import itertools
import random
from typing import Dict, List, Optional, Tuple

from backend.games.base_game import BaseGame


class BattleResult:
    """Simple battle result object"""

    def __init__(self, player1_name: str, player2_name: str):
        self.player1 = player1_name
        self.player2 = player2_name
        self.winner = None
        self.turns = []
        self.final_health = {}
        self.match_info = {}

    def add_turn(self, turn_data: Dict):
        self.turns.append(turn_data)

    def set_winner(self, winner_name: str):
        self.winner = winner_name

    def set_final_health(self, player1_health: int, player2_health: int):
        self.final_health = {self.player1: player1_health, self.player2: player2_health}

    def to_dict(self):
        return {
            "player1": self.player1,
            "player2": self.player2,
            "winner": self.winner,
            "turns": self.turns,
            "final_health": self.final_health,
            "match_info": self.match_info,
        }


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
        self.max_health = 25  # Health points
        self.dexterity = 25   # Dodge chance %
        self.health = self.max_health  # Current health
        
        # IMPORTANT: Store original attributes after setting custom values
        self._store_original_attributes()
        
        # Example builds:
        # Glass Cannon: attack=45, defense=5, max_health=25, dexterity=25
        # Tank: attack=10, defense=40, max_health=45, dexterity=5
        # Dodger: attack=25, defense=10, max_health=15, dexterity=50
    
    def make_combat_decision(self, opponent_stats, turn, your_role, last_opponent_action=None):
        # ROLE-BASED COMBAT: You are told if you're attacking or defending
        # your_role will be either "attacker" or "defender"
        
        # Access your own stats with self.health, self.attack, etc.
        # Opponent stats available in opponent_stats dict
        # turn = current turn number
        # last_opponent_action = what they did on their last turn
        
        hp_percentage = self.health / self.max_health
        
        if your_role == "attacker":
            # Attack Actions: 'attack', 'big_attack'
            if opponent_stats['health'] < 20 and hp_percentage > 0.5:
                self.add_feedback("Going for the kill with big attack!")
                return 'big_attack'
            else:
                self.add_feedback("Standard attack")
                return 'attack'
                
        elif your_role == "defender":
            # Defense Actions: 'defend', 'dodge', 'run_away'
            if hp_percentage < 0.2:
                self.add_feedback("Low health - running away!")
                return 'run_away'
            elif hp_percentage < 0.4:
                self.add_feedback("Defending to stay alive")
                return 'defend'
            else:
                self.add_feedback("Attempting to dodge")
                return 'dodge'
        else:
            raise ValueError(f"Invalid role: {your_role}")
"""

    game_instructions = """
# Arena Champions - Turn-Based Combat Programming Game

Design a champion that battles others in **turn-based** 1-on-1 combat through strategic programming.

## Tournament Structure (Home/Away System)
- **Each pair fights TWICE** (like soccer home/away matches)
- **Match 1**: Player A goes first, Player B goes second
- **Match 2**: Player B goes first, Player A goes second  
- **First player advantage**: Gets to act first in turn-based combat

## Turn-Based Combat System
- **Players alternate turns** - only ONE player acts per turn
- **Role-Based**: You're explicitly told if you're the "attacker" or "defender" each turn
- **Attacker**: Choose attack actions that affect the opponent
- **Defender**: Choose defensive actions to counter incoming attacks

## Character Creation
- Set your attributes directly in the `__init__` method
- Each attribute must be between **5 and 50**:
  - **attack**: Damage per strike
  - **defense**: Damage reduction percentage (capped at 90% effectiveness)
  - **max_health**: Total health points
  - **dexterity**: Dodge chance percentage

## Combat Actions (Based on Your Role)

### Attack Actions (when your_role == "attacker"):
- **attack**: Deal normal damage based on your attack stat to opponent
- **big_attack**: Deal double damage to opponent but lose 50% of your current health

### Defense Actions (when your_role == "defender"):
- **defend**: Reduce incoming damage by your defense percentage
- **dodge**: Attempt to completely avoid damage (dexterity% chance)
- **run_away**: Lose 50% of current health but become immune to this attack

## Combat Mechanics
- **Damage Calculation**: Base damage = your attack stat
- **Defense**: Reduces incoming damage by defense% (capped at 90% damage reduction)
- **Dodge**: dexterity% chance to completely avoid opponent's attack
- **Big Attack Cost**: Lose 50% of current HP when using big_attack
- **Running Away**: Lose 50% current HP, but become immune to this specific attack

## Programming Challenge
Implement:
1. `__init__()`: Set your character attributes (attack, defense, max_health, dexterity) between 5-50
   - **IMPORTANT**: Call `self._store_original_attributes()` after setting your custom attributes
2. `make_combat_decision()`: Choose your action based on your role using:
   - `your_role`: Either "attacker" or "defender" 
   - `self.health`, `self.attack`, etc. for your stats
   - `opponent_stats` dict for opponent information
   - `turn` number for turn-based strategy
   - `last_opponent_action` to react to what they just did

## Strategic Considerations
- **Role Awareness**: Different strategies for attacking vs defending
- **Turn Order Matters**: Going first in a match gives strategic advantage
- **Action Validation**: You can only use attack actions when attacking, defense actions when defending
- **Resource Management**: Big attacks and running away both cost health

## Leveling Up
- **Each win automatically adds +1 to ALL attributes**
- Plan your initial build knowing you'll become stronger with victories

## Strategy Tips
- **High Attack**: Deal more damage but consider survivability
- **High Defense**: Consistent damage reduction, good for defensive play
- **High Dexterity**: High-risk/high-reward - either dodge completely or take full damage
- **High Health**: More staying power, especially important for big_attack users
- **Adaptive Strategy**: Use different approaches when attacking vs defending

## Example Builds
- **Glass Cannon**: attack=45, defense=5, max_health=25, dexterity=25
- **Tank**: attack=10, defense=40, max_health=45, dexterity=5  
- **Dodge Master**: attack=25, defense=10, max_health=15, dexterity=50
- **Balanced**: attack=25, defense=25, max_health=25, dexterity=25
"""

    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        self.battle_history = {}
        self.game_feedback = {"game": "arena_champions", "battles": []}
        self.initialize_characters()

    def initialize_characters(self, validate_initial_attributes=True):
        """Initialize all characters using their attribute settings"""
        for player in self.players:
            player_name = str(player.name)

            # Original attributes are now stored automatically in Player.__init__()

            # Only validate player attributes at the start of simulation
            if validate_initial_attributes:
                try:
                    self._validate_player_attributes(player)
                except ValueError as e:
                    raise ValueError(f"Player {player_name}: {str(e)}")

            # Initialize game tracking attributes if they don't exist
            if not hasattr(player, "wins"):
                player.wins = 0
            if not hasattr(player, "losses"):
                player.losses = 0

            self.battle_history[player_name] = []

    def _validate_player_attributes(self, player):
        """Validate that player attributes are within allowed ranges"""
        attributes = ["attack", "defense", "max_health", "dexterity"]

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

    def get_player_action_with_role(
        self, player, opponent, turn: int, role: str, last_opponent_action: str = None
    ) -> str:
        """Get action from player with explicit role validation"""
        try:
            opponent_stats = opponent.get_combat_info()
            action = player.make_combat_decision(
                opponent_stats, turn, role, last_opponent_action
            )

            # Validate action matches role
            if not self.validate_action_for_role(action, role):
                valid_actions = (
                    ["attack", "big_attack"]
                    if role == "attacker"
                    else ["defend", "dodge", "run_away"]
                )
                self.add_feedback(
                    f"Invalid action '{action}' for role '{role}' from {player.name}. "
                    f"Valid actions: {valid_actions}. Defaulting to appropriate action."
                )
                # Default to appropriate action based on role
                action = "attack" if role == "attacker" else "defend"

            return action
        except Exception as e:
            self.add_feedback(f"Error getting action from {player.name}: {e}")
            return "attack" if role == "attacker" else "defend"

    def apply_action_effects(self, player, action: str) -> Dict:
        """Apply the effects of an action to a player"""
        effects = {"damage_dealt": 0, "health_cost": 0, "ran_away": False}

        if action == "big_attack":
            # Big attack costs 50% of current health
            health_cost = player.health // 2
            player.health -= health_cost
            effects["health_cost"] = health_cost
            effects["damage_dealt"] = player.attack * 2
        elif action == "attack":
            effects["damage_dealt"] = player.attack
        elif action == "run_away":
            # Running away costs 50% of current health
            health_cost = player.health // 2
            player.health -= health_cost
            effects["health_cost"] = health_cost
            effects["ran_away"] = True

        return effects

    def calculate_damage_taken(
        self, incoming_damage: int, defender, defense_action: str
    ) -> Tuple[int, str]:
        """Calculate final damage taken after defense"""
        # Scale down damage for balance
        incoming_damage = incoming_damage / 5

        if defense_action == "run_away":
            return 0, "ran away"

        if defense_action == "dodge":
            dodge_chance = min(defender.dexterity, 100)
            if random.randint(1, 100) <= dodge_chance:
                return 0, "dodged completely"
            else:
                return incoming_damage, "dodge failed"

        if defense_action == "defend":
            defense_reduction = min(defender.defense, 90) / 100
            final_damage = int(incoming_damage * (1 - defense_reduction))
            return (
                max(1, final_damage),
                f"defended (reduced by {min(defender.defense, 90)}%)",
            )

        # No defense
        return incoming_damage, "no defense"

    def resolve_combat_round(
        self,
        attacker,
        defender,
        attack_action: str,
        defend_action: str,
        ran_away_players: set,
    ) -> Dict:
        """Resolve a single round of combat with attacker and defender actions"""
        turn_result = {
            "attacker": str(attacker.name),
            "defender": str(defender.name),
            "attack_action": attack_action,
            "defend_action": defend_action,
            "effects": {},
            "health_after": {},
        }

        # Apply attacker's action effects first
        if attack_action == "big_attack":
            health_cost = attacker.health // 2
            attacker.health -= health_cost
            damage_to_deal = attacker.attack * 2
            turn_result["effects"]["attacker_health_cost"] = health_cost
        elif attack_action == "attack":
            damage_to_deal = attacker.attack
        else:
            damage_to_deal = 0  # Invalid attack action

        # Apply defender's response
        if defend_action == "run_away":
            health_cost = defender.health // 2
            defender.health -= health_cost
            ran_away_players.add(str(defender.name))
            final_damage = 0  # Running away negates the attack
            turn_result["effects"]["defender_health_cost"] = health_cost
            turn_result["effects"]["defender_ran_away"] = True
        else:
            # Calculate damage taken with defense
            final_damage, defense_msg = self.calculate_damage_taken(
                damage_to_deal, defender, defend_action
            )
            defender.health -= final_damage
            turn_result["effects"]["defense_result"] = defense_msg

        turn_result["effects"]["damage_dealt"] = final_damage
        turn_result["health_after"] = {
            str(attacker.name): max(0, attacker.health),
            str(defender.name): max(0, defender.health),
        }

        # Add player feedback
        feedback = {}
        if attacker.feedback:
            feedback[str(attacker.name)] = list(attacker.feedback)
            attacker.feedback = []
        if defender.feedback:
            feedback[str(defender.name)] = list(defender.feedback)
            defender.feedback = []

        if feedback:
            turn_result["feedback"] = feedback

        return turn_result

    def execute_combat(self, first_player, second_player) -> Tuple[str, BattleResult]:
        """Execute turn-based combat with explicit attacker/defender roles"""
        # Reset health for battle
        first_player.health = first_player.max_health
        second_player.health = second_player.max_health

        battle_result = BattleResult(str(first_player.name), str(second_player.name))

        turn_number = 0
        last_actions = {str(first_player.name): None, str(second_player.name): None}
        ran_away_players = set()

        while (
            first_player.health > 0 and second_player.health > 0 and turn_number < 100
        ):
            turn_number += 1

            # Determine who is attacker and defender this turn
            if turn_number % 2 == 1:
                attacker = first_player
                defender = second_player
            else:
                attacker = second_player
                defender = first_player

            # Skip turn if attacker ran away
            if str(attacker.name) in ran_away_players:
                continue

            # Get attacker's action
            attacker_last_opponent_action = last_actions.get(str(defender.name))
            attack_action = self.get_player_action_with_role(
                attacker,
                defender,
                turn_number,
                "attacker",
                attacker_last_opponent_action,
            )

            # Get defender's response (only if they haven't run away)
            defend_action = "no_defense"
            if str(defender.name) not in ran_away_players:
                defender_last_opponent_action = last_actions.get(str(attacker.name))
                defend_action = self.get_player_action_with_role(
                    defender,
                    attacker,
                    turn_number,
                    "defender",
                    defender_last_opponent_action,
                )

            # Resolve the combat round
            turn_result = self.resolve_combat_round(
                attacker, defender, attack_action, defend_action, ran_away_players
            )

            turn_result["turn"] = turn_number
            battle_result.add_turn(turn_result)

            # Update last actions
            last_actions[str(attacker.name)] = attack_action
            last_actions[str(defender.name)] = defend_action

            # Check for end conditions
            if len(ran_away_players) == 2:
                # Both ran away - highest health wins
                winner = (
                    str(first_player.name)
                    if first_player.health > second_player.health
                    else str(second_player.name)
                )
                battle_result.set_winner(winner)
                break

            if first_player.health <= 0 or second_player.health <= 0:
                break

        # Determine winner if battle didn't end early
        if not battle_result.winner:
            if first_player.health > 0:
                battle_result.set_winner(str(first_player.name))
            else:
                battle_result.set_winner(str(second_player.name))

        battle_result.set_final_health(first_player.health, second_player.health)
        return battle_result.winner, battle_result

    def _update_stats_and_history(
        self, winner_name: str, player1, player2, match_type: str
    ):
        """Helper method to update player stats and battle history"""
        if winner_name == str(player1.name):
            player1.wins += 1
            player2.losses += 1
            player1.level_up()
            self.add_feedback(
                f"{player1.name} wins {match_type} match vs {player2.name} and levels up!"
            )
        else:
            player2.wins += 1
            player1.losses += 1
            player2.level_up()
            self.add_feedback(
                f"{player2.name} wins away match vs {player1.name} and levels up!"
            )

        # Record battle history
        self.battle_history[str(player1.name)].append(
            {
                "opponent": str(player2.name),
                "result": ("win" if winner_name == str(player1.name) else "loss"),
                "match_type": match_type,
            }
        )
        self.battle_history[str(player2.name)].append(
            {
                "opponent": str(player1.name),
                "result": ("win" if winner_name == str(player2.name) else "loss"),
                "match_type": "away" if match_type == "home" else "home",
            }
        )

    def play_game(self, custom_rewards=None):
        """Play a complete tournament with proper home/away structure"""
        self.game_feedback = {"game": "arena_champions", "battles": []}

        # Initialize characters without validation (preserve leveled-up stats)
        self.initialize_characters(validate_initial_attributes=False)

        # FIXED: Use combinations to ensure each pair fights exactly twice
        for player1, player2 in itertools.combinations(self.players, 2):
            # Match 1: player1 goes first ("home" match for player1)
            winner_name, battle_result = self.execute_combat(player1, player2)
            battle_result.match_info = {
                "type": "home",
                "first_player": str(player1.name),
            }
            self.game_feedback["battles"].append(battle_result.to_dict())
            self._update_stats_and_history(winner_name, player1, player2, "home")

            # Match 2: player2 goes first ("home" match for player2)
            winner_name, battle_result = self.execute_combat(player2, player1)
            battle_result.match_info = {
                "type": "home",
                "first_player": str(player2.name),
            }
            self.game_feedback["battles"].append(battle_result.to_dict())
            self._update_stats_and_history(winner_name, player2, player1, "home")

        # Calculate final scores (wins)
        scores = {str(player.name): player.wins for player in self.players}

        # Calculate home vs away performance
        home_wins = {}
        away_wins = {}
        for player in self.players:
            player_name = str(player.name)
            home_wins[player_name] = sum(
                1
                for battle in self.battle_history[player_name]
                if battle["result"] == "win" and battle["match_type"] == "home"
            )
            away_wins[player_name] = sum(
                1
                for battle in self.battle_history[player_name]
                if battle["result"] == "win" and battle["match_type"] == "away"
            )

        # Create final stats - FLATTEN THE NESTED STRUCTURE FOR FRONTEND
        flattened_stats = {}
        for stat_name in [
            "attack",
            "defense",
            "max_health",
            "dexterity",
            "wins",
            "losses",
        ]:
            flattened_stats[stat_name] = {
                str(player.name): getattr(player, stat_name) for player in self.players
            }

        return {
            "points": scores,
            "score_aggregate": scores,
            "table": {
                **flattened_stats,  # ✅ SPREAD THE FLATTENED STATS
                "home_wins": home_wins,
                "away_wins": away_wins,
                "total_matches": {
                    p: len(self.battle_history[p]) for p in self.battle_history
                },
            },
        }

    def run_simulations(self, num_simulations, league, custom_rewards=None):
        """Run multiple simulations"""
        total_points = {str(player.name): 0 for player in self.players}
        total_wins = {str(player.name): 0 for player in self.players}

        for _ in range(num_simulations):
            self.reset()
            results = self.play_game(custom_rewards)

            for player, points in results['points'].items():
                total_points[str(player)] += points
                total_wins[str(player)] += points  # Since points = wins in this game

        return {
            "total_points": total_points,
            "num_simulations": num_simulations,
            "table": {
                "total_wins": total_wins,
                "avg_wins_per_sim": {
                    p: total_wins[p] / num_simulations for p in total_wins
                },
            },
        }

    def reset(self):
        """Reset game state - properly use base class reset"""
        super().reset()  # Handles base game reset (scores, feedback, etc.)
        self.reset_player_attributes()  # Restore original attributes
        self.battle_history = {}
        self.game_feedback = {"game": "arena_champions", "battles": []}

    def reset_player_attributes(self):
        """Reset all players to their original attribute values"""
        for player in self.players:
            player.reset_to_original_stats()
            player.wins = 0
            player.losses = 0
            self.battle_history[str(player.name)] = []

    def run_single_game_with_feedback(self, custom_rewards=None):
        """Run a single game with feedback"""
        self.verbose = True
        results = self.play_game(custom_rewards)
        return {
            "results": results,
            "feedback": self.game_feedback,
            "player_feedback": self.player_feedback,
        }
