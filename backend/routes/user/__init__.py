# Deliberately empty: a package-level re-export of user_router would drag the
# whole FastAPI route stack (~25MB) into any import of a single submodule
# (e.g. user_db) — memory that gets copy-on-write-faulted into every Celery
# worker fork (worker_max_tasks_per_child=1 forks a fresh child per task).
# Import user_router from backend.routes.user.user_router directly.
