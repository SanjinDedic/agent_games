#!/bin/bash

source ./setup_variables.sh

EXECUTABLE="api:app"
HOST="0.0.0.0"
PORT="8000"


if ! [ -x "$(command -v uvicorn)" ]; then
    echo "uvicorn is not installed. Installing uvicorn..."
    sudo apt install uvicorn
fi


# Create the service file
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOL
[Unit]
Description=Uvicorn instance to serve $SERVICE_NAME
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$WORKING_DIRECTORY

Restart=on-failure
RestartSec=5s

ExecStart=$VENV_DIRECTORY/bin/uvicorn $EXECUTABLE --host $HOST --port $PORT

Restart=always


[Install]
WantedBy=multi-user.target
EOL

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable $SERVICE_NAME

# Start the service
sudo systemctl start $SERVICE_NAME

# Provide status of the service
sudo systemctl status $SERVICE_NAME
