#!/usr/bin/env python3
"""
Arena Champions Local Simulator
Runs all validation players against each other in a round-robin tournament.
Each player fights every other player twice (home and away).
Shows concise battle results and final win totals.
"""

import sys
import os
import itertools

# Add the backend directory to Python path so we can import the game modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.games.arena_champions.arena_champions import ArenaChampionsGame
from backend.games.arena_champions.validation_players import players


def format_player_stats(player):
    """Format player stats for display"""
    return (f"HP: {player.health:.1f}/{player.max_health:.1f} | "
            f"ATK: {player.attack:.1f} | DEF: {player.defense:.1f} | DEX: {player.dexterity:.1f}")


def display_battle_header(player1, player2, battle_num, total_battles):
    """Display battle header with player information"""
    print("\n" + "="*80)
    print(f"BATTLE {battle_num}/{total_battles}: {player1.name} vs {player2.name}")
    print("="*80)
    print(f"Player 1 - {player1.name}:")
    print(f"  {format_player_stats(player1)}")
    print(f"Player 2 - {player2.name}:")
    print(f"  {format_player_stats(player2)}")
    print("-"*80)


def display_turn_info(turn_number, attacker, defender, attack_action, defend_action, turn_result):
    """Display detailed turn information"""
    print(f"\nTURN {turn_number}:")
    print(f"  Attacker: {attacker.name} -> {attack_action}")
    print(f"  Defender: {defender.name} -> {defend_action}")
    
    # Display feedback if available
    if 'feedback' in turn_result:
        for player_name, feedback_list in turn_result['feedback'].items():
            for feedback in feedback_list:
                print(f"    {player_name}: {feedback}")
    
    # Display effects
    effects = turn_result.get('effects', {})
    if 'attacker_health_cost' in effects:
        print(f"    {attacker.name} loses {effects['attacker_health_cost']:.1f} HP from big attack")
    
    damage_dealt = effects.get('damage_dealt', 0)
    defense_result = effects.get('defense_result', '')
    print(f"    Damage dealt: {damage_dealt:.1f} ({defense_result})")
    
    # Display health after turn
    health_after = turn_result.get('health_after', {})
    print(f"    Health after turn:")
    for player_name, health in health_after.items():
        print(f"      {player_name}: {health:.1f} HP")


def display_battle_result(winner, battle_result):
    """Display battle result"""
    print("\n" + "-"*40)
    print(f"BATTLE RESULT: {winner} WINS!")
    final_health = battle_result.final_health
    for player_name, health in final_health.items():
        status = "WINNER" if player_name == winner else "DEFEATED"
        print(f"  {player_name}: {health:.1f} HP ({status})")
    print("-"*40)


def run_single_battle(game, player1, player2):
    """Run a single battle between two players and return detailed results"""   
    # Execute the battle using the game's combat system
    winner, battle_result = game.execute_combat(player1, player2)
    
    return winner, battle_result


def main():
    """Main simulation function"""
    print("Arena Champions Local Simulator")
    print("===============================")
    print("NormalAttackNormalDefend will battle every other validation player")
    print("Press Enter after each battle to continue to the next one...")
    
    # Create the main player (our champion)
    main_player = players[0]  # NormalAttackNormalDefend
    
    # Create all other validation players
    other_players = players.copy()
    
    # Create a minimal game instance for combat mechanics
    # We'll use a simple league structure just to initialize the game
    class SimpleLeague:
        def __init__(self):
            pass
    
    game = ArenaChampionsGame(SimpleLeague(), verbose=True)
    
    # Battle statistics
    total_battles = len(other_players)
    wins = 0
    losses = 0
    
    print(f"\nTotal battles to fight: {total_battles}")
    input("\nPress Enter to start the battles...")
    
    # Fight each opponent
    for battle_num, opponent in enumerate(other_players, 1):
        # Display battle header
        display_battle_header(main_player, opponent, battle_num, total_battles)
        
        # Run the battle
        winner, battle_result = run_single_battle(game, main_player, opponent)
        
        # Display each turn in detail
        for turn_data in battle_result.turns:
            turn_number = turn_data['turn']
            attacker_name = turn_data['attacker']
            defender_name = turn_data['defender']
            attack_action = turn_data['attack_action']
            defend_action = turn_data['defend_action']
            
            # Determine which player object is the attacker/defender
            if attacker_name == main_player.name:
                attacker = main_player
                defender = opponent
            else:
                attacker = opponent
                defender = main_player
                
            display_turn_info(turn_number, attacker, defender, attack_action, defend_action, turn_data)
        
        # Display battle result
        display_battle_result(winner, battle_result)
        
        # Update statistics
        if winner == main_player.name:
            wins += 1
        else:
            losses += 1
        
        # Show current record
        print(f"\nCurrent record: {wins} wins, {losses} losses")
        
        # Wait for user input before next battle (except for last battle)
        if battle_num < total_battles:
            input("\nPress Enter to continue to the next battle...")
        
        # Reset players for next battle
        main_player.set_to_original_stats()
        opponent.set_to_original_stats()
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    print(f"{main_player.name} Record: {wins} wins, {losses} losses")
    win_percentage = (wins / total_battles) * 100 if total_battles > 0 else 0
    print(f"Win percentage: {win_percentage:.1f}%")
    
    if wins > losses:
        print(f"🏆 {main_player.name} dominated the arena!")
    elif wins == losses:
        print(f"⚖️ {main_player.name} had a balanced performance!")
    else:
        print(f"💪 {main_player.name} fought valiantly but has room for improvement!")
    
    print("\nSimulation complete!")


if __name__ == "__main__":
    main()
