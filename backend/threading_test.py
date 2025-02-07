import json
import os
import sys
import threading
import time
from datetime import datetime
from statistics import mean, stdev

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from backend.database.db_models import League
from backend.games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame


def create_test_league():
    """Create a test league for running simulations"""
    return League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now(),
        game="prisoners_dilemma",
    )


def run_single_simulation(game_class, league, results_dict, index):
    """Run a single simulation and store result in shared dictionary"""
    game = game_class(league)
    result = game.play_game()
    results_dict[index] = result


def run_threaded_simulations(num_sims, num_trials=3):
    """Run simulations using threads"""
    trial_times = []
    num_threads = min(4, num_sims)  # Use at most 4 threads

    for trial in range(num_trials):
        start_time = time.time()
        results = {}
        league = create_test_league()

        # Create and start threads in batches
        for batch_start in range(0, num_sims, num_threads):
            threads = []
            batch_end = min(batch_start + num_threads, num_sims)

            # Create threads for this batch
            for i in range(batch_start, batch_end):
                thread = threading.Thread(
                    target=run_single_simulation,
                    args=(PrisonersDilemmaGame, league, results, i),
                )
                threads.append(thread)
                thread.start()

            # Wait for all threads in this batch to complete
            for thread in threads:
                thread.join()

        end_time = time.time()
        trial_times.append(end_time - start_time)

    return mean(trial_times), stdev(trial_times)


def run_sequential_simulations(num_sims, num_trials=3):
    """Run simulations sequentially without threading"""
    trial_times = []

    for trial in range(num_trials):
        start_time = time.time()
        results = {}
        league = create_test_league()

        for i in range(num_sims):
            run_single_simulation(PrisonersDilemmaGame, league, results, i)

        end_time = time.time()
        trial_times.append(end_time - start_time)

    return mean(trial_times), stdev(trial_times)


def calculate_percentage_difference(time1, time2):
    """Calculate how much faster threaded execution is compared to sequential"""
    difference = abs(time1 - time2)
    percentage = (difference / max(time1, time2)) * 100

    if time1 < time2:
        return f"Threaded execution is {percentage:.1f}% faster than sequential"
    else:
        return f"Sequential execution is {percentage:.1f}% faster than threaded"


def run_performance_comparison(simulation_counts=[10, 100, 1000], num_trials=3):
    """Run complete performance comparison for different numbers of simulations"""
    results = {
        "threaded_results": [],
        "sequential_results": [],
        "threaded_stddev": [],
        "sequential_stddev": [],
        "simulation_counts": simulation_counts,
        "num_trials": num_trials,
        "comparisons": [],
        "test_parameters": {
            "timestamp": datetime.now().isoformat(),
        },
    }

    print(f"\nRunning benchmark with {num_trials} trials per test")

    for num_sims in simulation_counts:
        print(f"\nTesting with {num_sims} simulations:")

        # Run threaded test
        print("  Running threaded tests...")
        thread_time, thread_std = run_threaded_simulations(num_sims, num_trials)
        results["threaded_results"].append(round(thread_time, 2))
        results["threaded_stddev"].append(round(thread_std, 2))
        print(f"  Threaded time: {thread_time:.2f} ± {thread_std:.2f} seconds")

        # Run sequential test
        print("  Running sequential tests...")
        seq_time, seq_std = run_sequential_simulations(num_sims, num_trials)
        results["sequential_results"].append(round(seq_time, 2))
        results["sequential_stddev"].append(round(seq_std, 2))
        print(f"  Sequential time: {seq_time:.2f} ± {seq_std:.2f} seconds")

        # Calculate and display percentage difference
        comparison = calculate_percentage_difference(thread_time, seq_time)
        results["comparisons"].append(comparison)
        print(f"  {comparison}")

    # Save results to file
    filename = f'threading_benchmark_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to {filename}")

    return results


if __name__ == "__main__":
    # Run the performance comparison
    results = run_performance_comparison(
        simulation_counts=[10, 100, 1000], num_trials=3
    )
