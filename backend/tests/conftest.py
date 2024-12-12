# conftest.py (create this in your tests directory)
import os
import sys
import warnings

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings(
        "ignore", category=UserWarning, message=".*error reading bcrypt version.*"
    )
