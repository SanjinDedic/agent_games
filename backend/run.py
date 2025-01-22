import logging
import os
import sys
from pathlib import Path

import uvicorn

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Get the absolute path of the project root (one level up from backend)
ROOT_DIR = Path(__file__).parent.parent.absolute()
backend_dir = Path(__file__).parent.absolute()

# Add both project root and backend to Python path
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(backend_dir))

# Update PYTHONPATH environment variable if needed
if str(ROOT_DIR) not in os.environ.get("PYTHONPATH", ""):
    os.environ["PYTHONPATH"] = f"{ROOT_DIR}:{os.environ.get('PYTHONPATH', '')}"

logger.info(f"ROOT_DIR: {ROOT_DIR}")
logger.info(f"Backend dir: {backend_dir}")
logger.info(f"Python path: {sys.path}")

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
