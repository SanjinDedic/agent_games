FROM python:3.12

WORKDIR /agent_games

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application files
COPY . /agent_games/

# Run as non-root user
RUN useradd -m appuser
USER appuser

EXPOSE 8001

CMD ["python", "docker/services/validation_server.py"]