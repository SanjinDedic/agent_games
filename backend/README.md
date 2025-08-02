# 🎮 Multi-Game Simulation Platform
![Python](https://img.shields.io/badge/python-3.12-blue.svg)  [![Tests](https://github.com/SanjinDedic/agent_games/actions/workflows/test.yml/badge.svg)](https://github.com/SanjinDedic/agent_games/actions/workflows/test.yml)  [![codecov](https://codecov.io/gh/SanjinDedic/agent_games/graph/badge.svg?token=PWUU4GJSOD)](https://codecov.io/gh/SanjinDedic/agent_games)

## 🌟 Overview
The Multi-Game Simulation Platform is a Python-based project that allows users to simulate and play various games, starting with the popular dice game, Greedy Pig. The platform has been expanded to support multiple games and includes a front-end interface for enhanced user experience.

## 🚀 Getting Started

### Quick Start with Docker (Recommended)
The entire platform can be run locally with a single Docker Compose command:

1. Clone the repository: `git clone https://github.com/SanjinDedic/agent_games.git`
2. Navigate to the project directory: `cd agent_games`
3. Run the complete platform: `docker compose --profile dev up --build`

This single command will:
- Build and start all services (API, validator, simulator, frontend, database)
- Set up the PostgreSQL database with proper initialization
- Start the React frontend on `http://localhost:3000`
- Start the FastAPI backend on `http://localhost:8000`
- Automatically handle all dependencies and networking between services

### Manual Setup (Alternative)
If you prefer to run components individually:

1. Clone the repository: `git clone https://github.com/SanjinDedic/agent_games.git`
2. Install the required dependencies: `pip install -r requirements.txt`
3. Set up the database by running the database initialization script: `python initialize_db.py`
4. Start the FastAPI server: `PYTHONPATH=$PYTHONPATH:$(pwd | xargs dirname): uvicorn api:app --reload`
5. Access the platform through the provided front-end interface.

## 🎲 Available Games
- Greedy Pig: A simple dice game with interesting and unpredictable dynamics.
- Forty-Two: A card game where players aim to get as close to 42 points as possible without going over.

For more information on Greedy Pig, check out these resources:
- [The Statistical Problem of Greedy Pigs](https://www.smh.com.au/education/the-statistical-problem-of-greedy-pigs-20140728-3cpk8.html)
- [Optimal Play of the Dice Game "Pig"](https://cupola.gettysburg.edu/cgi/viewcontent.cgi?article=1003&context=csfac)

## 📚 Game Creation Guide
For collaborators interested in creating new games for the platform, please refer to our [Game Creation Guide](games/game_instructions.md). This document provides step-by-step instructions on how to implement and integrate a new game into the existing framework.
[*GAME CREATION GUIDE DOCUMENT*](games/game_instructions.md)

## 🏗️ Project Structure
The project is structured as follows:

- `api.py`: The main FastAPI application file that handles API endpoints and request handling.
- `auth.py`: Contains authentication-related functions and utilities.
- `config.py`: Stores configuration variables and settings for the project.
- `database.py`: Handles database operations and interactions.
- `models_db.py` and `models_api.py`: Define the database models and API schemas used in the project.
- `games/`: A directory that contains game-specific files and implementations.
  - `base_game.py`: The base class for all games.
  - `game_factory.py`: Factory class for creating game instances.
  - `greedy_pig/`: The Greedy Pig game implementation.
  - `prisoners_dilemma/`: Prisoners Dilemma game implementation
- `validation.py`: Contains validation functions for agent code and simulations.
- `requirements.txt`: Lists the project dependencies.

## 🌐 API Endpoints
The following API endpoints are available:

- `/`: Root endpoint for testing server status.
- `/league_create`: Creates a new league.
- `/league_join/{link}`: Allows users to join a league using a specific link.
- `/admin_login`: Handles admin login and authentication.
- `/team_login`: Handles team login and authentication.
- `/team_create`: Creates a new team (admin only).
- `/submit_agent`: Submits an agent code for a specific team.
- `/run_simulation`: Runs a simulation for a specific league (admin only).
- `/get_all_admin_leagues`: Retrieves all admin leagues.
- `/league_assign`: Assigns a team to a league.
- `/delete_team`: Deletes a team (admin only).
- `/get_all_teams`: Retrieves all teams.
- `/get_all_league_results`: Retrieves results for a specific league (admin only).
- `/publish_results`: Publishes simulation results for a league (admin only).
- `/get_published_results_for_league`: Retrieves published results for a specific league.
- `/get_published_results_for_all_leagues`: Retrieves published results for all leagues.
- `/update_expiry_date`: Updates the expiry date for a league (admin only).
- `/get_game_instructions`: Retrieves instructions for a specific game.

## 🔒 Security Features
The platform includes the following security features:

- Authentication and authorization using JSON Web Tokens (JWT).
- Password hashing using the `bcrypt` algorithm.
- Input validation and sanitization to prevent script injection and unauthorized access.
- CORS (Cross-Origin Resource Sharing) middleware for secure cross-origin requests.

## 🌐 Front-end Interface
The platform includes a user-friendly front-end interface built with modern web technologies. The front-end communicates with the FastAPI backend through API requests and provides an intuitive way for users to interact with the platform, create and join leagues, submit agents, and view simulation results.

## 🔧 Customization and Expansion
The Multi-Game Simulation Platform is designed to be easily customizable and expandable. You can add new games by following the steps outlined in the [Game Creation Guide](games/game_instructions.md).

## 💻 Manual Local Development

> **💡 Tip:** For most users, we recommend using the [one-command Docker setup](../README.md#-one-command-local-setup-recommended) from the main project directory instead of manual setup.

> **Note:** Use separate terminals for running the backend and frontend. Navigate to the respective directories (`cd backend` or `cd frontend`) in each terminal before running the commands.

### Backend Manual Setup

To run the backend locally without Docker, follow these steps:

1. **Create a Virtual Environment and Install Dependencies:**

    ```bash
    cd backend
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

2. **Build the Docker Image:**

    This step is crucial for secure code execution and simulations:

    ```bash
    docker build -t run-with-docker .
    ```

3. **Set Up the Production Database:**

    ```bash
    python3 production_database_setup.py
    ```

4. **Run the Uvicorn Server:**

    ```bash
    uvicorn api:app --reload
    ```

The backend server should now be running locally on `http://localhost:8000`. Game simulations will run in isolated Docker containers for security.

### Frontend Manual Setup

To run the frontend locally without Docker, follow these steps:

1. **Update the `.env` File:**

    Ensure your `.env` file is configured to use the local backend:

    ```env
    REACT_APP_AGENT_API_URL=http://localhost:8000
    ```

2. **Install Node.js Dependencies:**

    ```bash
    cd frontend
    npm install
    ```

3. **Run the Application:**

    If you encounter any issues, you may need to clear the npm cache and remove `node_modules`:

    ```bash
    npm cache clean --force
    rm -rf node_modules
    npm install
    ```

    Then start the application:

    ```bash
    npm start
    ```

The frontend should now be running locally and accessible via `http://localhost:3000`.

### Manual Setup Notes

- Make sure you have Python, Docker, Node.js, and npm installed on your machine
- Docker is required for running game simulations in secure containers
- The commands assume you're using a Unix-based system (Linux or macOS). Windows commands may differ slightly, especially for activating the virtual environment
- The backend server runs on port 8000 by default, and the frontend runs on port 3000
- Use different terminals for running backend and frontend processes when doing manual setup

## 🤝 Contributing
Contributions to the Multi-Game Simulation Platform are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request on the project's GitHub repository.

## 📄 License
This work is licensed under a [Creative Commons Attribution-NonCommercial 4.0 International License](http://creativecommons.org/licenses/by-nc/4.0/).

[Full license text](https://creativecommons.org/licenses/by-nc/4.0/legalcode)