#Deriving the latest base image
FROM python:latest

ENV SECRET_KEY="AGENTGAMES2024"

COPY games /agent_games/games
COPY requirements.txt /agent_games
COPY local_sim_api.py /agent_games
COPY models_db.py /agent_games
COPY config.py /agent_games
COPY auth.py /agent_games
COPY api.py /agent_games
COPY validation.py /agent_games
COPY models_api.py /agent_games
COPY utils.py /agent_games
COPY database.py /agent_games
COPY production_database_setup.py /agent_games

WORKDIR /agent_games

RUN pip install -r requirements.txt

CMD ["sh", "-c", "python production_database_setup.py && timeout 20s python local_sim_api.py"]