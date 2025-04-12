import asyncio
import logging
import time
from datetime import datetime, timedelta

import httpx
import pytest
from sqlmodel import Session

from backend.database.db_models import League, Team

pytestmark = pytest.mark.usefixtures("ensure_containers")


@pytest.fixture
def test_league(db_session: Session) -> League:
    """Create a test league for Docker service tests"""
    league = League(
        name="docker_test_league",
        game="prisoners_dilemma",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    return league


@pytest.fixture
def test_team(db_session: Session, test_league: League) -> Team:
    """Create a test team for Docker service tests"""
    team = Team(
        name="docker_test_team",
        school_name="Docker Test School",
        password_hash="test_hash",
        league_id=test_league.id,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


@pytest.mark.asyncio
async def test_validation_code_workflow(db_session: Session, test_team: Team):
    """Test complete code validation workflow."""

    # 1. Test invalid code with security violation
    invalid_security_code = """
from games.prisoners_dilemma.player import Player
import os  # Unauthorized import

class CustomPlayer(Player):
    def make_decision(self, game_state):
        os.system('echo "hack"')  # Should be caught by validator
        return "collude"
"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/validate",
            json={
                "code": invalid_security_code,
                "game_name": "prisoners_dilemma",
                "team_name": test_team.name,
                "num_simulations": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "unauthorized" in data["message"].lower()

        # 2. Test valid code
        valid_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "collude"
"""
        response = await client.post(
            "http://localhost:8001/validate",
            json={
                "code": valid_code,
                "game_name": "prisoners_dilemma",
                "team_name": test_team.name,
                "num_simulations": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "simulation_results" in data


@pytest.mark.asyncio
async def test_simulation_service_workflow(db_session: Session, test_league: League):
    """Test complete simulation workflow."""

    async with httpx.AsyncClient() as client:
        # Basic simulation
        response = await client.post(
            "http://localhost:8002/simulate",
            json={
                "league_id": test_league.id,
                "game_name": "prisoners_dilemma",
                "num_simulations": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "simulation_results" in data

        # Test with custom rewards
        response = await client.post(
            "http://localhost:8002/simulate",
            json={
                "league_id": test_league.id,
                "game_name": "prisoners_dilemma",
                "num_simulations": 10,
                "custom_rewards": [10, 5, 3, 0],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


@pytest.mark.asyncio
async def test_service_health_checks():
    """Test health of both services."""

    async with httpx.AsyncClient() as client:
        # Check validator health
        validator_response = await client.get("http://localhost:8001/health")
        assert validator_response.status_code == 200
        assert validator_response.json()["status"] == "healthy"

        # Check simulator health
        simulator_response = await client.get("http://localhost:8002/health")
        assert simulator_response.status_code == 200
        assert simulator_response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_service_error_recovery():
    """Test service recovery from errors."""

    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                "http://localhost:8001/validate",
                json={"code": "test"},
                timeout=0.001,  # Very short timeout
            )
            assert False, "Should have timed out"
        except httpx.TimeoutException:
            pass

        # Verify service still responsive after timeout
        response = await client.get("http://localhost:8001/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

        # Test invalid request handling
        response = await client.post(
            "http://localhost:8001/validate", json={}  # Invalid request
        )
        assert response.status_code == 422

        # Verify service still healthy
        health_response = await client.get("http://localhost:8001/health")
        assert health_response.status_code == 200


@pytest.mark.asyncio
async def test_service_error_recovery():
    """Test service recovery from errors."""

    async with httpx.AsyncClient(timeout=httpx.Timeout(1.0)) as client:
        # Test 1: Timeout handling using read timeout
        try:
            # Valid but computationally expensive code that will cause timeout
            timeout_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        # Computationally expensive operation
        result = 0
        for i in range(10000000):
            result += i
        return "collude"
"""
            await client.post(
                "http://localhost:8001/validate",
                json={
                    "code": timeout_code,
                    "game_name": "prisoners_dilemma",
                    "team_name": "test",
                    "num_simulations": 10000,  # Large number of simulations
                },
                timeout=httpx.Timeout(0.0001),  # Very short timeout
            )
            pytest.fail("Should have timed out")
        except httpx.TimeoutException:
            # Expected behavior
            pass

        # Test 2: Service still responsive after timeout
        health_response = await client.get(
            "http://localhost:8001/health",
            timeout=httpx.Timeout(5.0),  # Normal timeout for health check
        )
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "healthy"

        # Test 3: Invalid request handling
        response = await client.post(
            "http://localhost:8001/validate",
            json={
                "code": None,  # Invalid code
                "game_name": "prisoners_dilemma",
            },
        )
        assert response.status_code == 422  # Validation error

        # Test 4: Missing required fields
        response = await client.post(
            "http://localhost:8001/validate",
            json={},
        )
        assert response.status_code == 422

        # Test 5: Service remains healthy after errors
        health_response = await client.get("http://localhost:8001/health")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "healthy"

        # Test 6: Malformed JSON
        response = await client.post(
            "http://localhost:8001/validate",
            content=b"invalid json data",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

        # Test 7: Large invalid payload handling
        large_payload = {
            "code": "x" * 10000000,  # Very large code
            "game_name": "prisoners_dilemma",
            "team_name": "test",
            "num_simulations": 1,
        }
        response = await client.post(
            "http://localhost:8001/validate",
            json=large_payload,
            timeout=httpx.Timeout(10.0),  # Increased timeout for large payload
        )
        assert response.status_code in [
            413,
            422,
            200,
        ]  # Either payload too large or validation error
        assert response.json()["status"] == "error"


@pytest.mark.asyncio
async def test_concurrent_operations(db_session: Session, test_league: League):
    """Test handling of concurrent operations."""

    async with httpx.AsyncClient() as client:
        # Create multiple simulation tasks
        tasks = []
        for _ in range(5):
            task = client.post(
                "http://localhost:8002/simulate",
                json={
                    "league_id": test_league.id,
                    "game_name": "prisoners_dilemma",
                    "num_simulations": 10,
                },
            )
            tasks.append(task)

        # Run concurrently
        responses = await asyncio.gather(*tasks)

        # Verify all succeeded
        for response in responses:
            assert response.status_code == 200
            assert response.json()["status"] == "success"
