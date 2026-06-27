# Locust load-test runner for the submission benchmark.
# Build context is this folder; the locustfile is copied in.
FROM python:3.12-slim

RUN pip install --no-cache-dir locust

WORKDIR /loadtest
COPY locust_greedy_pig.py .

# All run params come from the environment / compose command override.
ENTRYPOINT ["locust", "-f", "locust_greedy_pig.py"]
