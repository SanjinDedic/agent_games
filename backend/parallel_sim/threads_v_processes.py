import json
import multiprocessing
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from statistics import mean, stdev

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame
from models_db import League


def create_test_league():
    """Create a test league for running simulations"""
    return League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        folder="leagues/test_league",
        game="prisoners_dilemma",
    )


def run_single_simulation(game_class, league, results_dict, index):
    """
    Run a single simulation and store result in shared dictionary

    Args:
        game_class: The game class to instantiate
        league: The league configuration to use
        results_dict: Shared dictionary to store results
        index: The index for storing this simulation's results
    """
    game = game_class(league)
    result = game.play_game()
    results_dict[index] = result


def thread_simulation_runner(num_sims, num_workers, num_trials=3):
    """
    Run simulations using pure threads with multiple trials for reliability

    Args:
        num_sims: Number of simulations to run
        num_workers: Number of concurrent workers to use
        num_trials: Number of times to repeat the test

    Returns:
        tuple: (average_time, std_dev)
    """
    trial_times = []

    for trial in range(num_trials):
        start_time = time.time()
        results = {}
        league = create_test_league()

        # Create and start threads in batches
        for batch_start in range(0, num_sims, num_workers):
            threads = []
            batch_end = min(batch_start + num_workers, num_sims)

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


def process_simulation_runner(num_sims, num_workers, num_trials=3):
    """
    Run simulations using pure processes with multiple trials for reliability

    Args:
        num_sims: Number of simulations to run
        num_workers: Number of concurrent workers to use
        num_trials: Number of times to repeat the test

    Returns:
        tuple: (average_time, std_dev)
    """
    trial_times = []

    for trial in range(num_trials):
        start_time = time.time()

        # Use Manager for sharing results between processes
        with multiprocessing.Manager() as manager:
            results = manager.dict()
            league = create_test_league()

            # Create and start processes in batches
            for batch_start in range(0, num_sims, num_workers):
                processes = []
                batch_end = min(batch_start + num_workers, num_sims)

                # Create processes for this batch
                for i in range(batch_start, batch_end):
                    process = multiprocessing.Process(
                        target=run_single_simulation,
                        args=(PrisonersDilemmaGame, league, results, i),
                    )
                    processes.append(process)
                    process.start()

                # Wait for all processes in this batch to complete
                for process in processes:
                    process.join()

            end_time = time.time()
            trial_times.append(end_time - start_time)

    return mean(trial_times), stdev(trial_times)


def calculate_percentage_difference(time1, time2):
    """
    Calculate how much faster one time is compared to another as a percentage

    Args:
        time1: First timing value
        time2: Second timing value

    Returns:
        str: Description of the percentage difference
    """
    difference = abs(time1 - time2)
    percentage = (difference / max(time1, time2)) * 100

    if time1 < time2:
        return f"Threads are {percentage:.1f}% faster than processes"
    else:
        return f"Processes are {percentage:.1f}% faster than threads"


def run_performance_comparison(num_simulations=10000, num_trials=3):
    """
    Run complete performance comparison with different numbers of workers

    Args:
        num_simulations: Number of simulations to run in each test
        num_trials: Number of trials to run for each configuration

    Returns:
        dict: Complete results of the performance comparison
    """
    worker_counts = [2, 4, 6, 8]
    results = {
        "thread_results": [],
        "process_results": [],
        "thread_stddev": [],
        "process_stddev": [],
        "worker_counts": worker_counts,
        "num_simulations": num_simulations,
        "num_trials": num_trials,
        "comparisons": [],
        "test_parameters": {
            "cpu_count": multiprocessing.cpu_count(),
            "timestamp": datetime.now().isoformat(),
        },
    }

    print(f"\nRunning {num_simulations} simulations with {num_trials} trials per test")
    print(f"System has {multiprocessing.cpu_count()} CPU cores")

    for num_workers in worker_counts:
        print(f"\nTesting with {num_workers} workers:")

        # Run thread test
        print("  Running thread tests...")
        thread_time, thread_std = thread_simulation_runner(
            num_simulations, num_workers, num_trials
        )
        results["thread_results"].append(round(thread_time, 2))
        results["thread_stddev"].append(round(thread_std, 2))
        print(f"  Thread time: {thread_time:.2f} ± {thread_std:.2f} seconds")

        # Run process test
        print("  Running process tests...")
        process_time, process_std = process_simulation_runner(
            num_simulations, num_workers, num_trials
        )
        results["process_results"].append(round(process_time, 2))
        results["process_stddev"].append(round(process_std, 2))
        print(f"  Process time: {process_time:.2f} ± {process_std:.2f} seconds")

        # Calculate and display percentage difference
        comparison = calculate_percentage_difference(thread_time, process_time)
        results["comparisons"].append(comparison)
        print(f"  {comparison}")

    # Save results to file
    filename = (
        f'parallel_comparison_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    )
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to {filename}")

    return results


if __name__ == "__main__":
    # Run the performance comparison with 100 simulations and 3 trials per test
    results = run_performance_comparison(num_simulations=10000, num_trials=3)
