# Greedy Pig Game Simulation Project

## Overview
The Greedy Pig Game Simulation is a Python-based project that simulates the popular dice game, Greedy Pig. This project includes a set of Python files that together create a framework for playing the game, testing game strategies, and handling game data through an API.

## Project Structure
The project consists of the following key components:

### 1. player_base.py
- **Purpose**: Defines the base `Player` class used to create player objects in the game. It includes methods for managing banked and unbanked money and tracking banking status.
- **Usage**: Used as a base class for creating different types of players in the game.

### 2. multi_player_game.py
- **Purpose**: Contains the core game logic, including the `Dice` class for rolling dice and the `Game` class for managing the game state, players, and rounds.
- **Usage**: Execute this file to run the game simulation with multiple players.

### 3. agent_send.py
- **Purpose**: Provides a testing framework for player decision-making algorithms. Includes the `Testing_Player` class and functionality to send this player's decisions to a specified server endpoint.
- **Usage**: Use this file to test different player strategies and decision-making algorithms.

### 4. api.py
- **Purpose**: Establishes an API for the game using FastAPI. Manages file uploads, CORS, rate limits, and integrates with the game simulation for additional functionalities.
- **Usage**: This API can be used to interact with the game simulation programmatically, providing an interface for external applications.

## Setup
To set up the Greedy Pig Game Simulation project, follow these steps:
1. Ensure you have Python installed on your system.
2. Download or clone this project to your local machine.
3. Install required dependencies (if any are listed in a `requirements.txt` file).

## Running the Simulation
- To run the game simulation, execute the `multi_player_game.py` file.
- Use `agent_send.py` to test different player strategies.
- Run `api.py` to start the FastAPI server and interact with the game via API calls.

## Contributing
Contributions to the project are welcome. Please follow standard git practices for branching and pull requests. Ensure that new code is well-documented and tested.

## License
MIT
