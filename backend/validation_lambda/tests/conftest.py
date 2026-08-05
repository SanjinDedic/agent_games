"""Fixtures for the validation-lambda test suite.

This directory holds every test that dies with the folder (executor
semantics, fork isolation, the Function-URL handler, browser-harness parity
incl. the per-game starter-code probe). It is not collected by the public
suite or CI — run it on demand:

    docker compose -f docker-compose.yml -f docker-compose.test.yml \
        run --rm test-runner pytest backend/validation_lambda/tests/ -v

The star-import re-exports the app/DB/Valkey fixtures from the main suite's
conftest — pytest_plugins outside the rootdir conftest is an error in modern
pytest, but importing the fixture objects works because they are plain module
attributes, autouse ones included. backend/tests/conftest.py's import-time
side effects (test env defaults, backend.api import) are wanted here too.

Known quirk: session-scoped fixtures (db_engine) re-register under this
directory, so a run sets up the test schema again when pytest enters this
folder — idempotent, just a few extra seconds.
"""

from backend.tests.conftest import *  # noqa: F401,F403
