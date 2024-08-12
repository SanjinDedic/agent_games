#!/bin/bash

cd ..

# Detect the current Python 3 version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

# Check if the appropriate venv package is installed for the detected Python version
if ! dpkg -l | grep -q "python${PYTHON_VERSION}-venv"; then
    echo "python${PYTHON_VERSION}-venv is not installed. Installing python${PYTHON_VERSION}-venv..."
    sudo apt-get install -y "python${PYTHON_VERSION}-venv"
fi

# Create a virtual environment
echo "Creating a virtual environment..."
python3 -m venv venv

# Activate the virtual environment
echo "Activating the virtual environment..."
source venv/bin/activate

# Install dependencies from requirements.txt
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "requirements.txt not found. Skipping dependency installation."
fi