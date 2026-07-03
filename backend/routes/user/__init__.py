# Deliberately empty: the Celery simulation task imports
# backend.routes.user.user_db inside the worker child (see
# backend/tasks/simulation_task.py), and a package-level re-export of
# user_router would drag the whole FastAPI route stack (~25MB) into that
# import — memory that gets copy-on-write-faulted on every fork
# (worker_max_tasks_per_child=1 forks a fresh child per task).
# Import user_router from backend.routes.user.user_router directly.
