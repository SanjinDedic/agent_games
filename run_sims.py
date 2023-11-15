import argparse
from multiple_players_game import run_simulation_many_times

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Run game simulations.")

    # Add arguments
    parser.add_argument('-sims', type=int, required=True, help='Number of simulations to run')
    args = parser.parse_args()



    # Run the simulation
    results = run_simulation_many_times(args.sims)

    # Print results
    print("Simulation Results:")
    print(results)

if __name__ == "__main__":
    main()