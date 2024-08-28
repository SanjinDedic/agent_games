# About

The project has transitioned to a monorepo structure with both the front end and back end combined. This README provides basic setup instructions for running the application locally. Detailed documentation will be added soon.

- [Front End Documentation](#)
- [Back End Documentation](#)
- [Server Deployment](#)

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
