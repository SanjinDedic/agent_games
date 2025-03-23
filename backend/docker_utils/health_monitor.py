# Add to backend/docker_utils/health_monitor.py

import asyncio
import logging
import time
from datetime import datetime

import httpx

from backend.docker_utils.containers import (
    ensure_containers_running,
    get_container_logs,
    stop_containers,
)

logger = logging.getLogger(__name__)


class ServiceMonitor:
    def __init__(self, check_interval=10, max_failures=3):
        self.check_interval = check_interval  # seconds between checks
        self.max_failures = max_failures
        self.failure_counts = {"validator": 0, "simulator": 0}
        self.last_restart = {"validator": None, "simulator": None}
        self.running = False

    async def check_service(self, name, port):
        """Check if a service is responding"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{port}/health",
                    timeout=3.0,
                )
                if response.status_code == 200:
                    # Service is healthy, reset failure count
                    self.failure_counts[name] = 0
                    return True
                else:
                    logger.warning(
                        f"{name} returned unhealthy status: {response.status_code}"
                    )
        except Exception as e:
            logger.warning(f"Failed to connect to {name}: {str(e)}")

        # Increment failure count
        self.failure_counts[name] += 1
        return False

    async def restart_if_needed(self, name):
        """Restart service if it has failed too many times"""
        if self.failure_counts[name] >= self.max_failures:
            now = datetime.now()

            # Don't restart too frequently (avoid restart loops)
            if (
                self.last_restart[name]
                and (now - self.last_restart[name]).total_seconds() < 60
            ):
                logger.warning(f"Not restarting {name} - too soon since last restart")
                return False

            logger.warning(
                f"Restarting {name} after {self.failure_counts[name]} failed health checks"
            )

            # Get logs before restart for debugging
            logs = get_container_logs(name)
            logger.info(f"{name} logs before restart:\n{logs}")

            # Stop and restart the containers
            stop_containers()
            ensure_containers_running()

            self.last_restart[name] = now
            self.failure_counts[name] = 0
            return True

        return False

    async def monitor_loop(self):
        """Main monitoring loop"""
        self.running = True
        logger.info("Service health monitoring started")

        while self.running:
            # Check validator
            validator_healthy = await self.check_service("validator", 8001)
            if not validator_healthy:
                await self.restart_if_needed("validator")

            # Check simulator
            simulator_healthy = await self.check_service("simulator", 8002)
            if not simulator_healthy:
                await self.restart_if_needed("simulator")

            # Wait until next check
            await asyncio.sleep(self.check_interval)

    def start(self):
        """Start the monitoring as a background task"""
        asyncio.create_task(self.monitor_loop())

    def stop(self):
        """Stop the monitoring loop"""
        self.running = False
