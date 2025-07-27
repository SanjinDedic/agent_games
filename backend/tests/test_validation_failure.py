import asyncio
import subprocess
import time

import httpx
import pytest


def ensure_services_running_direct():
    """Direct replacement for removed ensure_services_running function"""
    try:
        result = subprocess.run(
            ["docker", "compose", "--profile", "test", "up", "-d", "--wait"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


@pytest.mark.asyncio
async def test_malicious_agent_recovery():
    """Test that the health monitor can recover from a malicious agent submission"""
    try:
        # Use docker-compose to restart the services instead of removing them
        subprocess.run(["docker", "compose", "restart", "validator"], check=False)

        # Ensure services are running
        ensure_services_running_direct()

        # Wait for services to initialize - reduced to 2 seconds
        await asyncio.sleep(2)

        # Verify initial container is running
        initial_container_id = subprocess.run(
            ["docker", "compose", "ps", "-q", "validator"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert initial_container_id, "Validator service should be running initially"

        # Define health check function with shorter timeout
        async def check_health(port=8001):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"http://localhost:{port}/health",
                        timeout=1.0,  # Reduced timeout
                    )
                    return response.status_code == 200
            except Exception:
                return False

        # Verify initial health
        assert await check_health(
            8001
        ), "Validator service should be healthy before test"

        # Malicious code that will crash the validation server
        malicious_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        # Add feedback to track execution
        self.add_feedback("Starting malicious operation...")
        return self.recursive_memory_bomb(10000)
    
    def recursive_memory_bomb(self, depth):
        # Create a large list on each recursion to consume memory
        memory_eater = [i for i in range(1000000)]  # Allocate ~8MB per call
        
        # Make sure this reference stays alive in the call stack
        self.add_feedback(f"Recursion depth: {depth}, memory used: {len(memory_eater)} items")
        
        # Infinite recursion - never decreases depth
        return self.recursive_memory_bomb(depth)
"""

        print("Submitting malicious agent...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8001/validate",
                    json={
                        "code": malicious_code,
                        "game_name": "prisoners_dilemma",
                        "team_name": "MaliciousAgent",
                        "num_simulations": 1,
                    },
                    timeout=5.0,  # Reduced timeout
                )
            print(f"Response received: {response.status_code}")
        except Exception as e:
            print(f"Expected error during malicious submission: {e}")

        # Check that the service becomes unresponsive - reduced max wait time to 10 seconds
        print("Waiting for service to become unresponsive...")
        max_wait = 10  # Reduced from 30 seconds
        unresponsive = False
        polling_interval = 0.5  # Check more frequently

        start_time = time.time()
        while time.time() - start_time < max_wait:
            if not await check_health(8001):
                unresponsive = True
                break
            await asyncio.sleep(polling_interval)  # More frequent checks

        assert (
            unresponsive
        ), "Validator should become unresponsive after malicious submission"
        print(
            f"Validator service became unresponsive after {time.time() - start_time:.2f} seconds"
        )

        # Restart the validator service
        print("Restarting the validator service...")
        subprocess.run(["docker", "compose", "restart", "validator"], check=False)

        # Verify the service is healthy again - reduced max wait to 10 seconds
        max_wait = 10  # Reduced from 60 seconds
        healthy = False
        polling_interval = 0.5  # Check more frequently

        start_time = time.time()
        while time.time() - start_time < max_wait:
            if await check_health(8001):
                healthy = True
                recovery_time = time.time() - start_time
                print(f"Validator recovered in {recovery_time:.2f} seconds")
                break
            await asyncio.sleep(polling_interval)  # More frequent checks

        assert healthy, "Validator service should be healthy after restart"
        print("Test completed: System successfully recovered from malicious agent")

    except Exception as e:
        print(f"Unexpected error during test: {e}")
        raise
