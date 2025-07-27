import random
from typing import Dict

from backend.games.arena_champions.player import Player


class GlassCannon(Player):
    """High attack, low defense/HP build"""
    
    def distribute_points(self, available_points: int) -> Dict[str, int]:
        return {
            'attack': 70,
            'defense': 15,
            'hp': 15
        }
    
    def make_combat_decision(self, combat_state: Dict) -> str:
        # Aggressive strategy - always attack unless about to die
        hp_percentage = combat_state['my_current_hp'] / combat_state['my_max_hp']
        
        if hp_percentage < 0.2:
            self.add_feedback("Low HP - defending!")
            return 'defend'
        
        # Use power strike when opponent is low (if we can see)
        if combat_state.get('opponent_stats'):
            opp_hp_percent = combat_state['opponent_stats']['current_hp'] / combat_state['opponent_stats']['hp']
            if opp_hp_percent < 0.3 and combat_state['my_status'] == 'normal':
                self.add_feedback("Opponent low - power strike!")
                return 'power_strike'
        
        return 'attack'
    
    def level_up(self, points_to_distribute: int, current_stats: Dict, tournament_state: Dict) -> Dict[str, int]:
        # Continue focusing on attack
        return {
            'attack': points_to_distribute,
            'defense': 0,
            'hp': 0
        }


class TankBuild(Player):
    """High HP and defense, low attack"""
    
    def distribute_points(self, available_points: int) -> Dict[str, int]:
        return {
            'attack': 20,
            'defense': 40,
            'hp': 40
        }
    
    def make_combat_decision(self, combat_state: Dict) -> str:
        # Defensive strategy - alternate between attack and defend
        turn = combat_state['turns_elapsed']
        
        # Defend every other turn to maintain HP
        if turn % 2 == 0:
            self.add_feedback("Defensive turn - regenerating")
            return 'defend'
        
        # Analyze when we don't have preview
        if not combat_state.get('opponent_stats') and turn % 5 == 1:
            self.add_feedback("Gathering intel")
            return 'analyze'
        
        return 'attack'
    
    def level_up(self, points_to_distribute: int, current_stats: Dict, tournament_state: Dict) -> Dict[str, int]:
        # Boost HP for more tankiness
        return {
            'attack': 0,
            'defense': 2,
            'hp': 3
        }


class AdaptivePlayer(Player):
    """Adapts strategy based on opponent"""
    
    def distribute_points(self, available_points: int) -> Dict[str, int]:
        # Balanced start
        return {
            'attack': 35,
            'defense': 30,
            'hp': 35
        }
    
    def make_combat_decision(self, combat_state: Dict) -> str:
        hp_percentage = combat_state['my_current_hp'] / combat_state['my_max_hp']
        
        # If we have preview, adapt to opponent
        if combat_state.get('opponent_stats'):
            opp_stats = combat_state['opponent_stats']
            opp_hp_percent = opp_stats['current_hp'] / opp_stats['hp']
            
            # Against glass cannons (high attack, low hp)
            if opp_stats['hp'] < 25:
                if combat_state['my_status'] == 'normal' and opp_hp_percent < 0.5:
                    self.add_feedback("Finishing off glass cannon")
                    return 'power_strike'
                return 'attack'
            
            # Against tanks (high defense)
            if opp_stats['defense'] > 35:
                # Need sustained damage
                if hp_percentage < 0.5:
                    return 'defend'
                return 'attack'
        
        # Without preview, play cautiously
        if hp_percentage < 0.4:
            return 'defend'
        
        # Try to learn opponent HP periodically
        if not combat_state.get('opponent_stats') and combat_state['turns_elapsed'] % 4 == 0:
            return 'analyze'
        
        return 'attack'
    
    def level_up(self, points_to_distribute: int, current_stats: Dict, tournament_state: Dict) -> Dict[str, int]:
        # Adapt based on performance
        win_rate = current_stats['wins'] / max(1, current_stats['wins'] + current_stats['losses'])
        
        if win_rate < 0.4:
            # Losing too much - boost defense
            return {'attack': 1, 'defense': 3, 'hp': 1}
        elif win_rate > 0.6:
            # Winning - boost attack
            return {'attack': 3, 'defense': 1, 'hp': 1}
        else:
            # Balanced improvement
            return {'attack': 2, 'defense': 2, 'hp': 1}


class PatternDetector(Player):
    """Tries to detect and exploit opponent patterns"""
    
    def __init__(self):
        super().__init__()
        self.opponent_actions = []
    
    def distribute_points(self, available_points: int) -> Dict[str, int]:
        return {
            'attack': 40,
            'defense': 25,
            'hp': 35
        }
    
    def make_combat_decision(self, combat_state: Dict) -> str:
        # Record opponent action
        if combat_state['last_opponent_action']:
            self.opponent_actions.append(combat_state['last_opponent_action'])
        
        hp_percentage = combat_state['my_current_hp'] / combat_state['my_max_hp']
        
        # Emergency defend
        if hp_percentage < 0.25:
            return 'defend'
        
        # Look for patterns in last 3-5 moves
        if len(self.opponent_actions) >= 3:
            last_three = self.opponent_actions[-3:]
            
            # Opponent always defends after attack?
            if len(self.opponent_actions) >= 4:
                if (self.opponent_actions[-4] == 'attack' and 
                    self.opponent_actions[-2] == 'attack' and
                    self.opponent_actions[-3] == 'defend' and 
                    self.opponent_actions[-1] == 'defend'):
                    # They might defend next - power strike!
                    if combat_state['my_status'] == 'normal':
                        self.add_feedback("Pattern detected - they defend after attack!")
                        return 'power_strike'
            
            # Opponent spams same move?
            if all(action == last_three[0] for action in last_three):
                self.add_feedback(f"Opponent spamming {last_three[0]}")
                if last_three[0] == 'attack':
                    return 'defend'
                elif last_three[0] == 'defend':
                    return 'power_strike' if combat_state['my_status'] == 'normal' else 'attack'
        
        # Default strategy
        if not combat_state.get('opponent_stats') and len(self.opponent_actions) < 2:
            return 'analyze'
        
        return 'attack'
    
    def level_up(self, points_to_distribute: int, current_stats: Dict, tournament_state: Dict) -> Dict[str, int]:
        # Balanced improvement
        return {
            'attack': 2,
            'defense': 1,
            'hp': 2
        }


class RandomChaos(Player):
    """Unpredictable player to counter pattern detection"""
    
    def distribute_points(self, available_points: int) -> Dict[str, int]:
        # Random but valid distribution
        attack = random.randint(20, 50)
        defense = random.randint(15, 40)
        hp = available_points - attack - defense
        
        # Ensure minimums
        if hp < 5:
            excess = 5 - hp
            if attack > defense:
                attack -= excess
            else:
                defense -= excess
            hp = 5
        
        return {
            'attack': attack,
            'defense': defense,
            'hp': hp
        }
    
    def make_combat_decision(self, combat_state: Dict) -> str:
        hp_percentage = combat_state['my_current_hp'] / combat_state['my_max_hp']
        
        # Only defend when really low
        if hp_percentage < 0.15:
            return 'defend'
        
        # Can't power strike when recovering
        if combat_state['my_status'] == 'recovering':
            return random.choice(['attack', 'defend', 'analyze'])
        
        # Random choice weighted by situation
        choices = ['attack', 'attack', 'attack']  # Bias toward attack
        
        if hp_percentage < 0.5:
            choices.append('defend')
        
        if combat_state.get('opponent_stats'):
            opp_hp_percent = combat_state['opponent_stats']['current_hp'] / combat_state['opponent_stats']['hp']
            if opp_hp_percent < 0.3:
                choices.extend(['power_strike', 'power_strike'])
        else:
            choices.append('analyze')
        
        choice = random.choice(choices)
        self.add_feedback(f"Chaos chooses: {choice}")
        return choice
    
    def level_up(self, points_to_distribute: int, current_stats: Dict, tournament_state: Dict) -> Dict[str, int]:
        # Random distribution
        choices = [
            {'attack': 5, 'defense': 0, 'hp': 0},
            {'attack': 0, 'defense': 5, 'hp': 0},
            {'attack': 0, 'defense': 0, 'hp': 5},
            {'attack': 3, 'defense': 1, 'hp': 1},
            {'attack': 2, 'defense': 2, 'hp': 1},
        ]
        return random.choice(choices)


# List of players to be used for validation games
players = [
    GlassCannon(),
    TankBuild(),
    AdaptivePlayer(),
    PatternDetector(),
    RandomChaos(),
]