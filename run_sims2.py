import argparse
from run_animation import run_simulation_with_animation

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Run game simulations.")

    # Add arguments
    parser.add_argument('-sims', type=int, required=True, help='Number of simulations to run')
    parser.add_argument('-refresh', type=int, required=False, help='refresh rate for animation')
    # Parse arguments
    args = parser.parse_args()

    run_simulation_with_animation(number = args.sims, refresh_rate = args.refresh)

    # Run the simulation
    #results = run_simulation_many_times(args.sims)
    #top 5 nth times
    # Print results
    #print("Simulation Results:")
    #print(results)

if __name__ == "__main__":
    main()