#Deriving the latest base image
FROM python:latest

COPY games /agent_games/games
COPY requirements.txt /agent_games
COPY models_db.py /agent_games
COPY utils.py /agent_games
COPY config.py /agent_games
COPY auth.py /agent_games
COPY dockerfile_script.py /agent_games

WORKDIR /agent_games

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "dockerfile_script.py"]
