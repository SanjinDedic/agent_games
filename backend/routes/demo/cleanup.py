import logging
import threading
import time
from datetime import datetime

from sqlmodel import Session, create_engine

from backend.config import DEMO_TOKEN_EXPIRY, get_database_url
from backend.routes.demo.demo_db import (
    cleanup_expired_demo_users,
    cleanup_old_demo_submissions,
)

logger = logging.getLogger(__name__)


class DemoCleanupThread(threading.Thread):
    """Background thread that periodically cleans up expired demo data"""

    def __init__(self, interval_minutes=10):
        super().__init__(daemon=True)
        self.interval_minutes = interval_minutes
        self.stop_event = threading.Event()
        self.name = "DemoCleanupThread"

    def run(self):
        """Run the cleanup loop until stopped"""
        logger.info(
            f"Starting demo cleanup thread (interval: {self.interval_minutes} minutes)"
        )
        engine = create_engine(get_database_url())

        while not self.stop_event.is_set():
            try:
                self._perform_cleanup(engine)
            except Exception as e:
                logger.error(f"Error in demo cleanup thread: {str(e)}")

            # Sleep for the interval but check stop_event periodically
            self.stop_event.wait(timeout=self.interval_minutes * 60)

    def _perform_cleanup(self, engine):
        """Perform the actual cleanup operations"""
        logger.info(f"Running scheduled demo cleanup at {datetime.now()}")

        with Session(engine) as session:
            # Clean up old submissions
            submissions_deleted = cleanup_old_demo_submissions(
                session, DEMO_TOKEN_EXPIRY
            )

            # Clean up expired demo users
            users_deleted = cleanup_expired_demo_users(session, DEMO_TOKEN_EXPIRY)

            logger.info(
                f"Demo cleanup complete. Removed {submissions_deleted} old submissions and {users_deleted} expired users"
            )

    def stop(self):
        """Signal the thread to stop"""
        logger.info("Stopping demo cleanup thread")
        self.stop_event.set()


# Global cleanup thread instance
_cleanup_thread = None


def start_cleanup_thread():
    """Start the background cleanup thread if not already running"""
    global _cleanup_thread

    if _cleanup_thread is None or not _cleanup_thread.is_alive():
        _cleanup_thread = DemoCleanupThread()
        _cleanup_thread.start()
        logger.info("Demo cleanup thread started")


def stop_cleanup_thread():
    """Stop the background cleanup thread if running"""
    global _cleanup_thread

    if _cleanup_thread is not None and _cleanup_thread.is_alive():
        _cleanup_thread.stop()
        _cleanup_thread.join(timeout=5)
        logger.info("Demo cleanup thread stopped")
