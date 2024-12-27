# conftest.py
import os
import sys
import warnings
from pathlib import Path

# Add project root to PYTHONPATH
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings(
        "ignore", category=UserWarning, message=".*error reading bcrypt version.*"
    )
