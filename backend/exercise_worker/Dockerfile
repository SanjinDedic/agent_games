# Slim exercise worker: python + celery + the single tasks.py — nothing else.
# Build context is this directory (see docker-compose.yml), so the image can
# never accidentally pick up backend code, dependencies, or secrets.
FROM python:3.13-alpine

WORKDIR /app

# Pinned to the backend's locked celery version (uv.lock) so producer and
# consumer can't drift apart on wire behavior.
RUN pip install --no-cache-dir "celery[redis]==5.6.3"

# Non-root: this container executes unvalidated student code.
RUN addgroup -S worker && adduser -S worker -G worker
USER worker

COPY tasks.py .

# Prefork pool (the default; never --pool=solo here — solo silently ignores
# the task time limits that kill runaway submissions) with two child slots,
# so two exercises run concurrently.
CMD ["celery", "-A", "tasks", "worker", "-Q", "exercises", "-n", "exercises@%h", "--loglevel=info", "--concurrency=2"]
