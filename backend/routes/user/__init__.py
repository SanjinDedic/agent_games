# Deliberately empty: the Celery validation worker imports
# backend.routes.user.code_validation, and a package-level re-export of
# user_router would drag the whole FastAPI route stack (~25MB) into the worker
# parent — memory that gets copy-on-write-faulted on every fork
# (worker_max_tasks_per_child=1 forks a fresh child per task).
# Import user_router from backend.routes.user.user_router directly.
