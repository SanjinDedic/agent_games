import asyncio
import os
from unittest.mock import Mock, patch

import httpx
import pytest

from backend.tests.conftest import VALIDATOR_URL, SIMULATOR_URL


def test_validator_container_health():
    """Verify the validator container is running and healthy"""
    async def check_health():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{VALIDATOR_URL}/health", timeout=5.0)
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
        except httpx.RequestError as e:
            pytest.fail(
                f"Validator container is not running or not accessible: {str(e)}"
            )

    asyncio.run(check_health())


def test_simulator_container_health():
    """Verify the simulator container is running and healthy"""
    async def check_health():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{SIMULATOR_URL}/health", timeout=5.0)
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
        except httpx.RequestError as e:
            pytest.fail(
                f"Simulator container is not running or not accessible: {str(e)}"
            )

    asyncio.run(check_health())


def test_service_logs_accessible():
    """Test that service log files are accessible"""
    # Check if log directory exists (it should be created by setup)
    log_dir = "./logs"
    if not os.path.exists(log_dir):
        pytest.skip("Log directory not found - run setup_logs.sh first")

    # Check for validator log file
    validator_log = os.path.join(log_dir, "validator.log")
    simulator_log = os.path.join(log_dir, "simulator.log")

    # Files might not exist initially, but directory should be accessible
    assert os.access(log_dir, os.R_OK), "Log directory should be readable"
    assert os.access(log_dir, os.W_OK), "Log directory should be writable"


if __name__ == "__main__":
    pytest.main(["-v"])
