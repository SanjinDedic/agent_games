#!/bin/bash

cd ..

PYTHON_VERSION=$(python3 --version | awk '{print $2}' | cut -d. -f1,2)

# Replace the dot (.) with nothing to match the naming convention (e.g., 3.10 becomes 310)
PACKAGE_VERSION="python${PYTHON_VERSION}-venv"

# Check if the appropriate venv package is installed for the detected Python version
if ! dpkg -l | grep -q "$PACKAGE_VERSION"; then
    echo "$PACKAGE_VERSION is not installed. Installing $PACKAGE_VERSION..."
    sudo apt-get update
    sudo apt-get install -y "$PACKAGE_VERSION"
else
    echo "$PACKAGE_VERSION is already installed."
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