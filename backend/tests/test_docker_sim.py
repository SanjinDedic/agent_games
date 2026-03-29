import asyncio
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


if __name__ == "__main__":
    pytest.main(["-v"])
