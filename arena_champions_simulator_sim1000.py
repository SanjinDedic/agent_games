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


def run_battle(game, player1, player2):
    """Run a single battle between two players and return the result"""   
    winner, battle_result = game.execute_combat(player1, player2)
    final_health = battle_result.final_health
    
    player1_health = final_health.get(str(player1.name), 0)
    player2_health = final_health.get(str(player2.name), 0)
    
    return winner, player1_health, player2_health


def main():
    """Main simulation function"""
    print("Arena Champions Round-Robin Tournament Simulator")
    print("===============================================")
    print("Every player fights every other player twice (home and away)")
    print()
    
    # Create a minimal game instance for combat mechanics
    class SimpleLeague:
        def __init__(self):
            pass
    
    game = ArenaChampionsGame(SimpleLeague(), verbose=False)
    
    # Track wins for each player
    win_counts = {str(player.name): 0 for player in players}
    total_battles = 0
    
    print("Battle Results:")
    print("-" * 60)
    
    # Fight each pair twice (home and away)
    for player1, player2 in itertools.combinations(players, 2):
        # Reset players to original stats before each battle
        player1.set_to_original_stats()
        player2.set_to_original_stats()
        
        # Battle 1: player1 goes first
        winner, p1_health, p2_health = run_battle(game, player1, player2)
        print(f"{player1.name}(H) vs {player2.name}(A) | {winner} WON | {player1.name}: {p1_health:.1f} HP | {player2.name}: {p2_health:.1f} HP")
        win_counts[winner] += 1
        total_battles += 1
        
        # Reset players again
        player1.set_to_original_stats()
        player2.set_to_original_stats()
        
        # Battle 2: player2 goes first
        winner, p2_health, p1_health = run_battle(game, player2, player1)
        # Note: battle_result uses player order as passed to execute_combat
        # So we need to swap the health values for display
        print(f"{player2.name}(H) vs {player1.name}(A) | {winner} WON | {player1.name}: {p1_health:.1f} HP | {player2.name}: {p2_health:.1f} HP")
        win_counts[winner] += 1
        total_battles += 1
    
    # Display final results
    print("\n" + "=" * 60)
    print("FINAL TOURNAMENT RESULTS (Single Round-Robin)")
    print("=" * 60)
    print(f"Total battles fought: {total_battles}")
    print("\nWin counts:")
    
    # Sort players by wins (descending)
    sorted_players = sorted(win_counts.items(), key=lambda x: x[1], reverse=True)
    
    for rank, (player_name, wins) in enumerate(sorted_players, 1):
        win_percentage = (wins / total_battles * len(players)) * 100 if total_battles > 0 else 0
        print(f"{rank:2d}. {player_name:<20} {wins:2d} wins ({win_percentage:.1f}%)")
    
    # Now run 100 simulations to level out dodge performance
    print("\n" + "=" * 80)
    print("RUNNING 100 SIMULATIONS TO LEVEL OUT DODGE PERFORMANCE...")
    print("=" * 80)
    print("This may take a moment...")
    
    # Create a proper league instance for simulations
    class SimulationLeague:
        def __init__(self):
            pass
    
    # Run the simulations using the game's built-in method
    sim_game = ArenaChampionsGame(SimulationLeague(), verbose=False)
    sim_game.players = players  # Set the players
    sim_results = sim_game.run_simulations(1000, SimulationLeague())
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS AFTER 1000 SIMULATIONS")
    print("=" * 60)
    print(f"Total simulations run: {sim_results['num_simulations']}")
    print("\nTotal wins across all simulations:")
    
    # Sort by total wins across all simulations
    sim_sorted = sorted(sim_results['total_points'].items(), key=lambda x: x[1], reverse=True)
    
    for rank, (player_name, total_wins) in enumerate(sim_sorted, 1):
        avg_wins = sim_results['table']['avg_wins_per_sim'][player_name]
        print(f"{rank:2d}. {player_name:<20} {total_wins:3d} total wins ({avg_wins:.2f} avg per sim)")
    
    print("\nSimulation complete!")


if __name__ == "__main__":
    main()
