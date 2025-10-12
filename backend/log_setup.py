"""Utility to ensure log directory and log files exist.

This prevents Docker from creating directories in place of files when bind mounting
and makes first–time setup seamless across platforms.
"""
from __future__ import annotations
from pathlib import Path
import shutil
from typing import Iterable

LOG_DIR = Path("/agent_games/logs")  # Path inside the container
LOG_FILES: Iterable[str] = ("api.log", "validator.log", "simulator.log")

def ensure_log_files():
    """Create log directory and empty log files if missing.

    If a path that should be a file is (accidentally) a directory, remove it
    and recreate it as an empty file. This mirrors what collaborators expect
    when they first clone the repo and run docker compose.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for name in LOG_FILES:
        target = LOG_DIR / name
        if target.is_dir():
            # Remove mistaken directory so we can create a file instead
            shutil.rmtree(target)
        if not target.exists():
            target.touch()

__all__ = ["ensure_log_files", "LOG_FILES", "LOG_DIR"]
