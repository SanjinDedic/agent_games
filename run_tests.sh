#!/bin/bash
# Run tests via docker compose
# Usage:
#   ./run_tests.sh                          # Run all tests
#   ./run_tests.sh backend/tests/integration/routes/auth/test_auth.py -v  # Run specific test
#   ./run_tests.sh --cov=backend --cov-report=term backend/tests/        # With coverage

set -e

if [ $# -eq 0 ]; then
    docker compose --profile test run --rm test-runner
else
    docker compose --profile test run --rm test-runner pytest "$@"
fi
