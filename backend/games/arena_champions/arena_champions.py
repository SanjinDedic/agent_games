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
        # Distribute proportions between 0.2 and 0.4 and keep the sum <= 1.0
        self.attack_proportion = 0.30
        self.defense_proportion = 0.20
        self.max_health_proportion = 0.25
        self.dexterity_proportion = 0.25
        self.set_to_original_stats()

    
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
            # Defense Actions: 'defend', 'dodge', 'brace'
            if hp_percentage < 0.2:
                self.add_feedback("Low health - running away!")
                return 'brace'
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
# Arena Champions — concise rules and RPS matchup

Program a fighter and battle 1v1 in turns. Each turn has clear roles:
- Attacker chooses an attack.
- Defender chooses a response.
You may only use attack actions as attacker and defense actions as defender.

## Build your champion (5–50 each)
- attack: base damage
- defense: damage reduction (capped)
- max_health: total HP
- dexterity: dodge chance and precision

## Actions
- Attacker: attack, big_attack, precise_attack
- Defender: defend, dodge, brace

## Rock–Paper–Scissors (RPS) core
- Each attack is strong vs one defense, weak vs another; the third is neutral.
- Each defense is strong vs one attack, weak vs another; the third is neutral.

### Matchup table
```
|                | defend | brace  | dodge  |
|----------------|:------:|:------:|:------:|
| attack         | neutral|  weak  | strong |
| big_attack     | strong | neutral|  weak  |
| precise_attack |  weak  | strong | neutral|
```

## Notes
- Dodge can fully avoid hits (chance scales with dexterity).
- Big attack trades reliability for burst and may self-penalize.
- Precise attack trades raw damage for accuracy/armor-pierce potential.
- Each win can level up your stats (+1 each).
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
        """Validate player attributes are within allowed ranges"""
        if not (0.2 <= player.attack_proportion <= 0.4):
            raise ValueError(
                f"Invalid attack proportion for {player.name}: {player.attack_proportion}"
            )
        if not (0.2 <= player.defense_proportion <= 0.4):
            raise ValueError(
                f"Invalid defense proportion for {player.name}: {player.defense_proportion}"
            )
        if not (0.2 <= player.dexterity_proportion <= 0.4):
            raise ValueError(
                f"Invalid dexterity proportion for {player.name}: {player.dexterity_proportion}"
            )
        if not (0.2 <= player.max_health_proportion <= 0.4):
            raise ValueError(
                f"Invalid max health proportion for {player.name}: {player.max_health_proportion}"
            )
        if (
            not player.max_health_proportion
            + player.attack_proportion
            + player.defense_proportion
            + player.dexterity_proportion
            <= 1.0
        ):
            raise ValueError(
                f"Total proportions for {player.name} exceed 1.0: "
                f"{player.attack_proportion + player.defense_proportion + player.dexterity_proportion + player.max_health_proportion}"
            )

    @staticmethod
    def validate_action_for_role(action: str, role: str) -> bool:
        """Validate that the action is appropriate for the given role"""
        attack_actions = ["attack", "big_attack", "precise_attack"]
        defense_actions = ["defend", "dodge", "brace"]

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
                    ["attack", "big_attack", "precise_attack"]
                    if role == "attacker"
                    else ["defend", "dodge", "brace"]
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

    def calculate_damage(
        self, attacker, defender, attack_action: str, defense_action: str
    ) -> Tuple[int, str]:
        """Calculate final damage taken using rock-paper-scissors defense system"""
        base_damage = attacker.attack
        min_damage = 10

        # tweak these figures until the game is blanced (min 6000 wind and max 9000 wins)
        big_attack_multiplier = 2.33  # Big attack multiplier
        precise_attack_multiplier = 0.55
        def_vs_precise_attack_multiplier = 1.3
        def_vs_big_attack_reducer = 0.3  # Defense effectiveness vs big attack
        brace_vs_attack_multiplier = 0.65  # Brace effectiveness vs regular attack
        brace_vs_precise_attack_multiplier = 0.5  # Brace effectiveness vs big attack

        # Attack modifiers
        if attack_action == "big_attack":
            # Big attack doubles damage but increases opponent's defense
            base_damage *= big_attack_multiplier
            attacker.health = attacker.health / 2 - 1  # Lose 50% health
        elif attack_action == "precise_attack":
            # Enhanced by dexterity
            base_damage += attacker.dexterity * precise_attack_multiplier

        # Defense handling with effectiveness system
        if defense_action == "dodge":
            # Dodge chance enhanced by dexterity
            dodge_chance = min(defender.dexterity * 1.5, 75)
            if random.randint(0, 100) <= dodge_chance:
                return 0, "dodged completely"
            # Effectiveness after failed dodge
            if attack_action == "big_attack":
                final_damage = base_damage * 0.7  # Strong vs big attack
                msg = "dodge failed but reduced big attack damage"
            elif attack_action == "precise_attack":
                final_damage = base_damage  # Average vs precise
                msg = "dodge failed, moderate damage from precise attack"
            else:  # regular attack
                final_damage = base_damage * 1.2  # Weak vs regular
                msg = "dodge failed, vulnerable to regular attack"

        elif defense_action == "defend":
            if attack_action == "precise_attack":
                final_damage = (
                    base_damage - defender.defense * def_vs_precise_attack_multiplier
                )
                msg = f"strong defense vs precise attack ({defender.defense * 1.5} blocked)"
            elif attack_action == "attack":
                final_damage = 10 + base_damage - defender.defense  # Average vs regular
                msg = f"defended normally ({defender.defense} blocked)"
            else:  # big_attack
                final_damage = (
                    base_damage - defender.defense * def_vs_big_attack_reducer
                )  # Weak vs big
                msg = f"defense overwhelmed by big attack ({defender.defense} blocked)"

        elif defense_action == "brace":
            if attack_action == "attack":
                final_damage = (
                    base_damage * brace_vs_attack_multiplier
                )  # Strong vs regular
                msg = "braced effectively vs regular attack"
            elif attack_action == "big_attack":
                final_damage = base_damage
                msg = "braced with moderate effectiveness vs big attack"
            else:  # precise_attack
                final_damage = base_damage * brace_vs_precise_attack_multiplier
                msg = "brace vulnerable to precise attack"
        else:
            # No defense
            final_damage = base_damage
            msg = "no defense"
        return max(min_damage, final_damage), msg

    def resolve_combat_round(
        self,
        attacker,
        defender,
        attack_action: str,
        defend_action: str,
    ) -> Dict:
        """Resolve a single round of combat with attacker and defender actions"""
        turn_result = {
            "attacker": str(attacker.name),
            "defender": str(defender.name),
            "attack_action": attack_action,
            "defend_action": defend_action,
            "effects": {},
            "health_before": {
                str(attacker.name): max(0, attacker.health),
                str(defender.name): max(0, defender.health),
            },
            "health_after": {},
        }

        # Calculate damage the defender takes
        final_damage, defense_msg = self.calculate_damage(
            attacker, defender, attack_action, defend_action
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
                attacker, defender, attack_action, defend_action
            )

            turn_result["turn"] = turn_number
            battle_result.add_turn(turn_result)

            # Update last actions
            last_actions[str(attacker.name)] = attack_action
            last_actions[str(defender.name)] = defend_action

            if first_player.health <= 0 or second_player.health <= 0:
                break

        # Determine winner if battle didn't end early. The second player wins the tie if both players are at/below 0 hp
        if not battle_result.winner:
            if first_player.health > 0:
                battle_result.set_winner(str(first_player.name))
            else:
                battle_result.set_winner(str(second_player.name))

        battle_result.set_final_health(first_player.health, second_player.health)
        # reset health after battle to prevent bugs
        first_player.health = first_player.max_health
        second_player.health = second_player.max_health

        return battle_result.winner, battle_result

    def _update_stats_and_history(
        self, winner_name: str, player1, player2, match_type: str
    ):
        """Helper method to update player stats and battle history"""
        if winner_name == str(player1.name):
            player1.wins += 1
            player2.losses += 1
            # player1.level_up(1)
            # player2.level_up(0.8)  # No level up for loser
            self.add_feedback(
                f"{player1.name} wins {match_type} match vs {player2.name} and levels up!"
            )
        else:
            player2.wins += 1
            player1.losses += 1
            # player2.level_up()
            # player1.level_up(0.8)  # No level up for loser
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
        self.initialize_characters(validate_initial_attributes=True)

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
            player.set_to_original_stats()
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
