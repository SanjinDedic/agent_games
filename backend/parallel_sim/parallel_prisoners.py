import asyncio
from concurrent.futures import ProcessPoolExecutor
import time
from datetime import datetime, timedelta

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame
from models_db import League

def run_single_simulation(custom_rewards):
    test_league = League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        folder="leagues/test_league",
        game="prisoners_dilemma"
    )
    
    game = PrisonersDilemmaGame(test_league)
    return game.play_game(custom_rewards)

def run_sequential_simulations(num_sims, custom_rewards=None):
    start_time = time.time()
    
    for _ in range(num_sims):
        run_single_simulation(custom_rewards)
        
    end_time = time.time()
    return end_time - start_time

async def run_parallel_simulations(num_sims, max_workers=8, custom_rewards=None):
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(executor, run_single_simulation, custom_rewards)
            for _ in range(num_sims)
        ]
        await asyncio.gather(*futures)
    
    end_time = time.time()
    return end_time - start_time

async def main():
    num_sims = 100000
    custom_rewards = [4, 0, 6, 2]  # Optional custom rewards
    
    print(f"\nRunning {num_sims} sequential simulations...")
    sequential_time = run_sequential_simulations(num_sims, custom_rewards)
    print(f"Sequential execution time: {sequential_time:.2f} seconds")
    
    print(f"\nRunning {num_sims} parallel simulations with 8 workers...")
    parallel_time = await run_parallel_simulations(num_sims, 4, custom_rewards)
    print(f"Parallel execution time: {parallel_time:.2f} seconds")
    
    speedup = sequential_time / parallel_time
    print(f"\nSpeedup factor: {speedup:.2f}x")

if __name__ == "__main__":
    asyncio.run(main())