import asyncio
import subprocess
import time

import httpx
import pytest


@pytest.mark.asyncio  # Add this marker to tell pytest-asyncio to handle this test
async def test_malicious_agent_recovery():
    """Test that the health monitor can recover from a malicious agent submission"""
    # 1. Start with a clean state - ensure containers are running properly
    subprocess.run(["docker", "rm", "-f", "validator"], check=False)
    subprocess.run(["docker", "rm", "-f", "simulator"], check=False)
    from backend.docker_utils.containers import ensure_containers_running

    ensure_containers_running()

    # Wait for containers to fully initialize
    await asyncio.sleep(5)

    # 2. Get initial container ID
    initial_container_id = subprocess.run(
        ["docker", "ps", "-q", "-f", "name=validator"], capture_output=True, text=True
    ).stdout.strip()

    assert initial_container_id, "Validator container should be running initially"

    # 3. Verify initial health
    async def check_health(port=8001):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{port}/health", timeout=2.0
                )
                return response.status_code == 200
        except Exception:
            return False

    assert await check_health(8001), "Validator container should be healthy before test"

    # 4. Submit the malicious agent that will crash the validation server
    malicious_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        \"\"\"
        This implementation will cause stack overflow through infinite recursion
        while also consuming memory rapidly.
        \"\"\"
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
                timeout=10.0,  # Longer timeout to ensure request is processed
            )
        print(f"Response received: {response.status_code}")
    except Exception as e:
        print(f"Expected error during malicious submission: {e}")

    # 5. Check that the service becomes unresponsive
    print("Waiting for service to become unresponsive...")
    max_wait = 30  # seconds
    unresponsive = False

    start_time = time.time()
    while time.time() - start_time < max_wait:
        if not await check_health(8001):
            unresponsive = True
            break
        await asyncio.sleep(1)

    assert (
        unresponsive
    ), "Validator should become unresponsive after malicious submission"
    print("Validator service is now unresponsive as expected")

    # 6. Wait for the health monitor to detect failures and restart the container
    # The ContainerHealthMonitor class should be running in the main application
    print("Waiting for automatic container recovery...")
    await asyncio.sleep(
        30
    )  # Give the health monitor time to detect failures and restart

    # 7. Check if container was restarted
    new_container_id = subprocess.run(
        ["docker", "ps", "-q", "-f", "name=validator"], capture_output=True, text=True
    ).stdout.strip()

    # Container should be running (ID might be the same or different depending on restart method)
    assert new_container_id, "Validator container should be running after recovery"
    print(f"Initial container ID: {initial_container_id}")
    print(f"New container ID: {new_container_id}")

    # 8. Verify the new container is healthy
    max_wait = 30  # seconds
    healthy = False

    start_time = time.time()
    while time.time() - start_time < max_wait:
        if await check_health(8001):
            healthy = True
            break
        await asyncio.sleep(1)

    assert healthy, "Validator container should be healthy after restart"
    print("Test completed: System successfully recovered from malicious agent")
