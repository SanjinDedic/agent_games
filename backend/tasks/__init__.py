# All Celery code lives in this package: app/config (celery_app), result
# polling (celery_utils), and the task modules (validation_task,
# simulation_task). Deliberately no re-exports: the worker parent imports
# this package on every fork path (worker_max_tasks_per_child=1), so anything
# imported here is copy-on-write-faulted into every task child. Import from
# the submodules directly.
