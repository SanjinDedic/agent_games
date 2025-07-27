import json
import random
from typing import Dict, List, Optional, Tuple

from backend.games.base_game import BaseGame


class ArenaChampionsGame(BaseGame):
    starter_code = """
from games.arena_champions.player import Player
import random

class CustomPlayer(Player):
    def distribute_points(self, available_points):
        # Initial distribution of 100 points
        # Must return dict with 'attack', 'defense', 'hp'
        # Minimum 5 points per attribute
        
        # Example: Balanced build
        return {
            'attack': 35,
            'defense': 30,
            'hp': 35
        }
    
    def make_combat_decision(self, combat_state):
        # Available actions: 'attack', 'defend', 'power_strike', 'analyze'
        # combat_state contains:
        # - my_current_hp, my_max_hp, my_attack, my_defense
        # - opponent_stats (if has_preview is True): attack, defense, hp, current_hp
        # - turns_elapsed, last_opponent_action
        # - my_status (e.g., 'normal' or 'recovering')
        
        # Simple strategy: attack when healthy, defend when low
        hp_percentage = combat_state['my_current_hp'] / combat_state['my_max_hp']
        
        if hp_percentage < 0.3:
            return 'defend'
        elif combat_state.get('opponent_stats') and combat_state['opponent_stats']['current_hp'] < 20:
            return 'power_strike'
        else:
            return 'attack'
    
    def level_up(self, points_to_distribute, current_stats, tournament_state):
        # Distribute 5 points after winning
        # tournament_state contains info about remaining opponents
        
        # Example: Boost attack
        return {
            'attack': points_to_distribute,
            'defense': 0,
            'hp': 0
        }
"""

    game_instructions = """
# Arena Champions - Combat Programming Game

Design a champion that battles others in 1-on-1 combat through strategic programming.

## Character Creation
- You start with 100 points to distribute among:
  - **Attack**: Damage per strike
  - **Defense**: Damage reduction (capped at 80% effectiveness)
  - **HP**: Total health points
- Minimum 5 points per attribute

## Combat Actions
Each turn, choose one action:
- **attack**: Deal damage based on your attack stat
- **defend**: Take 50% less damage this turn, regenerate 10% max HP
- **power_strike**: Deal 1.5x damage but skip next turn
- **analyze**: Deal 0.5x damage, learn opponent's current HP

## Preview System
- Each pair fights twice
- One player gets full opponent stats in first match
- Roles reverse in rematch
- Use this information advantage wisely!

## Programming Challenge
Implement three methods:
1. `distribute_points()`: Initial character build
2. `make_combat_decision()`: Turn-by-turn combat AI
3. `level_up()`: Distribute 5 points after each win

## Strategy Tips
- Detect opponent patterns
- Manage HP wisely
- Time power strikes carefully
- Balance offense and defense
- Adapt based on preview information
"""

    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        self.character_stats = {}  # Stores persistent character stats
        self.level_ups = {}  # Tracks available level-up points
        self.battle_history = {}  # Stores battle outcomes
        self.game_feedback = {"game": "arena_champions", "battles": []}
        self.initialize_characters()

    def initialize_characters(self):
        """Initialize all characters with their starting stats"""
        for player in self.players:
            player_name = str(player.name)
            
            # Get initial point distribution
            try:
                distribution = player.distribute_points(100)
                # Validate distribution
                if not self._validate_distribution(distribution, 100):
                    # Use default balanced distribution if invalid
                    distribution = {'attack': 35, 'defense': 30, 'hp': 35}
            except Exception as e:
                self.add_feedback(f"Error in {player_name} point distribution: {e}")
                distribution = {'attack': 35, 'defense': 30, 'hp': 35}
            
            self.character_stats[player_name] = {
                'attack': distribution['attack'],
                'defense': distribution['defense'],
                'hp': distribution['hp'],
                'max_hp': distribution['hp'],
                'current_hp': distribution['hp'],
                'wins': 0,
                'losses': 0
            }
            self.level_ups[player_name] = 0
            self.battle_history[player_name] = []

    def _validate_distribution(self, distribution: Dict, total_points: int) -> bool:
        """Validate point distribution"""
        if not all(key in distribution for key in ['attack', 'defense', 'hp']):
            return False
        
        if sum(distribution.values()) != total_points:
            return False
        
        if any(val < 5 for val in distribution.values()):
            return False
        
        return True

    def calculate_damage(self, attacker_stats: Dict, defender_stats: Dict, multiplier: float = 1.0) -> int:
        """Calculate damage with defense reduction"""
        base_damage = attacker_stats['attack'] * multiplier
        defense_factor = min(defender_stats['defense'] / 100, 0.8)  # Cap at 80%
        damage = max(1, int(base_damage * (1 - defense_factor)))
        return damage

    def execute_combat(self, player1, player2, player1_has_preview: bool) -> Tuple[str, Dict]:
        """Execute a single combat between two players"""
        p1_name = str(player1.name)
        p2_name = str(player2.name)
        
        # Copy current stats for battle
        p1_stats = self.character_stats[p1_name].copy()
        p2_stats = self.character_stats[p2_name].copy()
        p1_stats['current_hp'] = p1_stats['max_hp']
        p2_stats['current_hp'] = p2_stats['max_hp']
        
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
        p1_skip_next = False
        p2_skip_next = False
        
        turn = 0
        last_p1_action = None
        last_p2_action = None
        
        while p1_stats['current_hp'] > 0 and p2_stats['current_hp'] > 0 and turn < 100:
            turn += 1
            turn_data = {'turn': turn, 'actions': {}}
            
            # Player 1 turn
            if not p1_skip_next:
                combat_state = self._create_combat_state(
                    p1_stats, p2_stats if player1_has_preview else None,
                    turn, last_p2_action, p1_status, True
                )
                
                try:
                    p1_action = player1.make_combat_decision(combat_state)
                    if p1_action not in ['attack', 'defend', 'power_strike', 'analyze']:
                        p1_action = 'attack'
                except Exception as e:
                    self.add_feedback(f"Error in {p1_name} combat decision: {e}")
                    p1_action = 'attack'
                
                turn_data['actions'][p1_name] = p1_action
                last_p1_action = p1_action
            else:
                p1_skip_next = False
                p1_status = 'normal'
                turn_data['actions'][p1_name] = 'recovering'
            
            # Player 2 turn
            if not p2_skip_next:
                combat_state = self._create_combat_state(
                    p2_stats, p1_stats if not player1_has_preview else None,
                    turn, last_p1_action, p2_status, False
                )
                
                try:
                    p2_action = player2.make_combat_decision(combat_state)
                    if p2_action not in ['attack', 'defend', 'power_strike', 'analyze']:
                        p2_action = 'attack'
                except Exception as e:
                    self.add_feedback(f"Error in {p2_name} combat decision: {e}")
                    p2_action = 'attack'
                
                turn_data['actions'][p2_name] = p2_action
                last_p2_action = p2_action
            else:
                p2_skip_next = False
                p2_status = 'normal'
                turn_data['actions'][p2_name] = 'recovering'
            
            # Resolve actions
            p1_defending = p1_action == 'defend' if not p1_skip_next else False
            p2_defending = p2_action == 'defend' if not p2_skip_next else False
            
            # Apply damage
            if not p1_skip_next:
                if p1_action == 'attack':
                    damage = self.calculate_damage(p1_stats, p2_stats)
                    if p2_defending:
                        damage = damage // 2
                    p2_stats['current_hp'] -= damage
                    turn_data[f'{p1_name}_damage'] = damage
                
                elif p1_action == 'power_strike':
                    damage = self.calculate_damage(p1_stats, p2_stats, 1.5)
                    if p2_defending:
                        damage = damage // 2
                    p2_stats['current_hp'] -= damage
                    p1_skip_next = True
                    p1_status = 'recovering'
                    turn_data[f'{p1_name}_damage'] = damage
                
                elif p1_action == 'analyze':
                    damage = self.calculate_damage(p1_stats, p2_stats, 0.5)
                    if p2_defending:
                        damage = damage // 2
                    p2_stats['current_hp'] -= damage
                    turn_data[f'{p1_name}_damage'] = damage
                    turn_data[f'{p1_name}_learned_hp'] = p2_stats['current_hp']
            
            if not p2_skip_next:
                if p2_action == 'attack':
                    damage = self.calculate_damage(p2_stats, p1_stats)
                    if p1_defending:
                        damage = damage // 2
                    p1_stats['current_hp'] -= damage
                    turn_data[f'{p2_name}_damage'] = damage
                
                elif p2_action == 'power_strike':
                    damage = self.calculate_damage(p2_stats, p1_stats, 1.5)
                    if p1_defending:
                        damage = damage // 2
                    p1_stats['current_hp'] -= damage
                    p2_skip_next = True
                    p2_status = 'recovering'
                    turn_data[f'{p2_name}_damage'] = damage
                
                elif p2_action == 'analyze':
                    damage = self.calculate_damage(p2_stats, p1_stats, 0.5)
                    if p1_defending:
                        damage = damage // 2
                    p1_stats['current_hp'] -= damage
                    turn_data[f'{p2_name}_damage'] = damage
                    turn_data[f'{p2_name}_learned_hp'] = p1_stats['current_hp']
            
            # Apply healing from defend
            if p1_defending:
                heal = int(p1_stats['max_hp'] * 0.1)
                p1_stats['current_hp'] = min(p1_stats['current_hp'] + heal, p1_stats['max_hp'])
                turn_data[f'{p1_name}_healed'] = heal
            
            if p2_defending:
                heal = int(p2_stats['max_hp'] * 0.1)
                p2_stats['current_hp'] = min(p2_stats['current_hp'] + heal, p2_stats['max_hp'])
                turn_data[f'{p2_name}_healed'] = heal
            
            # Record HP
            turn_data['hp'] = {
                p1_name: max(0, p1_stats['current_hp']),
                p2_name: max(0, p2_stats['current_hp'])
            }
            
            battle_log['turns'].append(turn_data)
            
            # Add player feedback
            if player1.feedback:
                self.add_player_feedback(player1, turn, p2_name)
            if player2.feedback:
                self.add_player_feedback(player2, turn, p1_name)
        
        # Determine winner
        if p1_stats['current_hp'] > 0:
            battle_log['winner'] = p1_name
            return p1_name, battle_log
        else:
            battle_log['winner'] = p2_name
            return p2_name, battle_log

    def _create_combat_state(self, my_stats: Dict, opponent_stats: Optional[Dict], 
                           turn: int, last_opponent_action: Optional[str], 
                           my_status: str, has_preview: bool) -> Dict:
        """Create the combat state for a player"""
        state = {
            'my_current_hp': my_stats['current_hp'],
            'my_max_hp': my_stats['max_hp'],
            'my_attack': my_stats['attack'],
            'my_defense': my_stats['defense'],
            'turns_elapsed': turn,
            'last_opponent_action': last_opponent_action,
            'my_status': my_status,
            'has_preview': has_preview
        }
        
        if opponent_stats:
            state['opponent_stats'] = {
                'attack': opponent_stats['attack'],
                'defense': opponent_stats['defense'],
                'hp': opponent_stats['max_hp'],
                'current_hp': opponent_stats['current_hp']
            }
        
        return state

    def apply_level_up(self, player, player_name: str):
        """Apply level up points after a win"""
        if self.level_ups[player_name] > 0:
            current_stats = self.character_stats[player_name].copy()
            tournament_state = {
                'battles_completed': len(self.battle_history[player_name]),
                'wins': self.character_stats[player_name]['wins'],
                'remaining_battles': 28 - len(self.battle_history[player_name])
            }
            
            try:
                distribution = player.level_up(5, current_stats, tournament_state)
                if self._validate_distribution(distribution, 5):
                    self.character_stats[player_name]['attack'] += distribution.get('attack', 0)
                    self.character_stats[player_name]['defense'] += distribution.get('defense', 0)
                    hp_increase = distribution.get('hp', 0)
                    self.character_stats[player_name]['hp'] += hp_increase
                    self.character_stats[player_name]['max_hp'] += hp_increase
                    self.level_ups[player_name] -= 5
                    
                    self.add_feedback(f"{player_name} leveled up: +{distribution}")
            except Exception as e:
                self.add_feedback(f"Error in {player_name} level up: {e}")

    def play_game(self, custom_rewards=None):
        """Play a complete tournament"""
        self.game_feedback = {"game": "arena_champions", "battles": []}
        self.initialize_characters()
        
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
                    self.character_stats[winner_name]['wins'] += 1
                    self.character_stats[loser_name]['losses'] += 1
                    self.level_ups[winner_name] += 5
                    
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
                    self.character_stats[winner_name]['wins'] += 1
                    self.character_stats[loser_name]['losses'] += 1
                    self.level_ups[winner_name] += 5
                    
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
        for player_name in self.character_stats:
            scores[player_name] = self.character_stats[player_name]['wins']
        
        # Additional stats for the table
        total_damage = {}
        for battle in self.game_feedback['battles']:
            for turn in battle['turns']:
                for key, value in turn.items():
                    if '_damage' in key:
                        player = key.replace('_damage', '')
                        total_damage[player] = total_damage.get(player, 0) + value
        
        return {
            'points': scores,
            'score_aggregate': scores,
            'table': {
                'final_stats': {p: self.character_stats[p] for p in self.character_stats},
                'total_damage': total_damage,
                'battles_fought': {p: len(self.battle_history[p]) for p in self.battle_history}
            }
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
        """Reset game state"""
        super().reset()
        self.character_stats = {}
        self.level_ups = {}
        self.battle_history = {}
        self.game_feedback = {"game": "arena_champions", "battles": []}
        self.initialize_characters()

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