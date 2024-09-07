# Agent Games

This project is a monorepo containing both the frontend and backend for the Agent Games application.

## Frontend

![React](https://img.shields.io/badge/React-18.x-61DAFB?logo=react&logoColor=white)
![Redux](https://img.shields.io/badge/Redux-4.x-764ABC?logo=redux&logoColor=white)
![React Router](https://img.shields.io/badge/React_Router-6.x-CA4245?logo=react-router&logoColor=white)
![Monaco Editor](https://img.shields.io/badge/Monaco_Editor-0.30.x-00B3E6?logo=visual-studio-code&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-Authentication-000000?logo=json-web-tokens&logoColor=white)


The frontend is built with React and Redux, offering a user interface for game submission, league management, and result viewing. It features code editing capabilities and responsive design.

For more details, see the [Frontend README](./frontend/README.md).

## Backend

![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95.1-009688.svg?logo=fastapi)
![Pydantic](https://img.shields.io/badge/Pydantic-2.14.7-E92063.svg?logo=pydantic)
![SQLite](https://img.shields.io/badge/SQLite-3.39.4-003B57.svg?logo=sqlite)
![Docker](https://img.shields.io/badge/Docker-20.10.21-2496ED.svg?logo=docker&logoColor=white)
[![Tests](https://github.com/SanjinDedic/agent_games/actions/workflows/test.yml/badge.svg)](https://github.com/SanjinDedic/agent_games/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/SanjinDedic/agent_games/graph/badge.svg?token=PWUU4GJSOD)](https://codecov.io/gh/SanjinDedic/agent_games)

The backend is powered by FastAPI, handling game logic, user authentication, and data management. It includes Docker integration for simulations and uses SQLite for data storage.

For more information, check out the [Backend README](./backend/README.md).

## Getting Started

For instructions on how to set up and run the project locally, please refer to the respective README files in the frontend and backend directories.

## Running the App Locally

> **Note:** Use separate terminals for running the backend and frontend. Navigate to the respective directories (`cd backend` or `cd frontend`) in each terminal before running the commands.

### Backend

To run the backend locally, follow these steps:

1. **Create a Virtual Environment and Install Dependencies:**

    ```bash
    cd backend
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

2. **Build the Docker Image:**

    After installing the dependencies, build the Docker image:

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

The backend server should now be running locally on `http://localhost:8000`.

### Frontend

To run the frontend locally, follow these steps:

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

## Notes

- Make sure you have Python, Docker, Node.js, and npm installed on your machine.
- The commands for setting up the backend and frontend assume you're using a Unix-based system (Linux or macOS). Windows commands may differ slightly, especially for activating the virtual environment.
- The backend server runs on port 8000 by default, and the frontend runs on port 3000.
- Use different terminals for running backend and frontend processes to avoid command conflicts.
