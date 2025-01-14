FROM python:3.12

WORKDIR /backend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create non-root user and group
RUN groupadd -r simgroup && useradd -r -g simgroup simuser

# Install requirements and curl
RUN apt-get update && apt-get install -y curl

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application files
COPY . /backend/

# Set ownership of the working directory and all files
RUN chown -R simuser:simgroup /backend

# Switch to non-root user
USER simuser

EXPOSE 8002

CMD ["python", "docker_utils/services/simulation_server.py"]