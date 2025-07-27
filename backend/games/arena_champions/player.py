from abc import ABC, abstractmethod
from typing import Dict


class Player(ABC):
    def __init__(self):
        self.name = self.__class__.__name__
        self.feedback = []

    def add_feedback(self, message):
        """Add feedback that will be visible in the game output"""
        self.feedback.append(message)

    @abstractmethod
    def distribute_points(self, available_points: int) -> Dict[str, int]:
        """
        Distribute initial points among attack, defense, and hp.
        
        Args:
            available_points: Total points to distribute (100 at start)
            
        Returns:
            Dictionary with keys 'attack', 'defense', 'hp'
            Each value must be at least 5
            Sum must equal available_points
        """
        pass

    @abstractmethod
    def make_combat_decision(self, combat_state: Dict) -> str:
        """
        Make a combat decision based on current battle state.
        
        Args:
            combat_state: Dictionary containing:
                - my_current_hp: Your current HP
                - my_max_hp: Your maximum HP
                - my_attack: Your attack stat
                - my_defense: Your defense stat
                - turns_elapsed: Number of turns so far
                - last_opponent_action: Opponent's last action (if any)
                - my_status: 'normal' or 'recovering' (from power strike)
                - has_preview: Whether you can see opponent stats
                - opponent_stats (if has_preview): Dict with attack, defense, hp, current_hp
                
        Returns:
            One of: 'attack', 'defend', 'power_strike', 'analyze'
        """
        pass

    @abstractmethod
    def level_up(self, points_to_distribute: int, current_stats: Dict, tournament_state: Dict) -> Dict[str, int]:
        """
        Distribute points gained from winning a battle.
        
        Args:
            points_to_distribute: Points to allocate (always 5)
            current_stats: Your current stats (attack, defense, hp, max_hp, wins, losses)
            tournament_state: Information about tournament progress
                - battles_completed: Number of battles finished
                - wins: Your total wins
                - remaining_battles: Battles left in tournament
                
        Returns:
            Dictionary with keys 'attack', 'defense', 'hp'
            Sum must equal points_to_distribute
        """
        pass