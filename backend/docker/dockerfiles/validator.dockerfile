FROM python:3.12

WORKDIR /agent_games

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy necessary files
COPY games /agent_games/games
COPY models_db.py /agent_games
COPY utils.py /agent_games
COPY config.py /agent_games
COPY auth.py /agent_games
COPY docker/services/validation_server.py /agent_games/validation_server.py

# Expose the port the app runs on
EXPOSE 8001

# Set the entrypoint to run the validation server
ENTRYPOINT ["python", "validation_server.py"]