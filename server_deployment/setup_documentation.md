# Agent Games Server Setup Documentation

This documentation provides an overview of the setup process for agent games server installation, which includes the creation and configuration of a setting up python environment, Dockerized Python service, the setup of SSL certificates using Certbot, and the configuration of Apache. The setup is automated using a series of bash scripts.

## Table of Contents

- [Overview](#overview)
- [Files and Their Purpose](#files-and-their-purpose)
  - [setup.sh](#setupsh)
  - [setup_variables.sh](#setup_variablessh)
  - [configure_python.sh](#configure_python)
  - [configure_service.sh](#configure_servicesh)
  - [configure_certbot.sh](#configure_certbotsh)
  - [configure_apache.sh](#configure_apachesh)
- [Running the Setup](#running-the-setup)
- [Dependencies](#dependencies)
- [Troubleshooting](#troubleshooting)

## Overview

The setup process for this project is managed through a series of bash scripts that automate the configuration and deployment of a Python-based application running on Uvicorn, with SSL support through Certbot, and served via Apache.

The main entry point is the `setup.sh` script, which orchestrates the execution of other configuration scripts: `setup_variables.sh`, `configure_python.sh`, `configure_service.sh`, `configure_certbot.sh`, and `configure_apache.sh`. Each of these scripts performs specific tasks necessary to set up the environment and ensure the application is correctly configured and running.

## Files and Their Purpose

### setup.sh

`setup.sh` is the primary script that initiates the entire setup process. It performs the following functions:

- **Environment Installation**: Executes `configure_python.sh` to configure python virtual environment with its dependencies.
- **Docker Installation**: Checks if Docker is installed and installs it if necessary. It also builds the Docker image for the application.
- **Variable Sourcing**: Sources environment variables from `setup_variables.sh`.
- **Service Configuration**: Executes `configure_service.sh` to set up and start the systemd service for the application.
- **Certbot Configuration**: Runs `configure_certbot.sh` to obtain SSL certificates for the domain.
- **Apache Configuration**: Executes `configure_apache.sh` to configure the Apache web server with SSL.

### setup_varaiables.sh

`setup_variables.sh` contains the environment variables needed for the setup process. These variables are sourced by the `setup.sh` script and include:

- **Certbot Variables**: Defines the domain and email address used for obtaining SSL certificates.
- **Service Variables**: Defines variables related to the systemd service configuration, such as the service name, user, working directory, and virtual environment directory.

### configure_python.sh

is a script designed to automate the setup of a Python virtual environment, ensuring that the correct version of Python and its associated `venv` package are used. The script performs the following tasks:

- **Python Version Detection**: Detects the current version of Python 3 installed on the system to ensure compatibility with the virtual environment.
- **Virtual Environment Package Installation**: Checks if the appropriate `python-venv` package is installed for the detected Python version. If not, it installs the necessary package to support the creation of virtual environments.
- **Virtual Environment Creation**: Creates a new Python virtual environment in the `venv` directory using the detected Python version.
- **Virtual Environment Activation**: Activates the newly created virtual environment, preparing it for use in the current shell session.
- **Dependency Installation**: Checks for the presence of a `requirements.txt` file and installs any listed dependencies using `pip`. If `requirements.txt` is not found, it skips the installation step.


### configure_service.sh

`configure_service.sh` is responsible for setting up the systemd service that runs the Uvicorn server for the Python application. The script performs the following tasks:

- **Uvicorn Installation**: Checks if Uvicorn is installed and installs it if necessary.
- **Service Creation**: Creates a systemd service file using the variables sourced from `setup_variables.sh`.
- **Service Management**: Reloads systemd to recognize the new service, enables it to start on boot, and starts the service.

### configure_certbot.sh

`configure_certbot.sh` manages the process of obtaining SSL certificates using Certbot. The script includes the following steps:

- **Certbot Installation**: Installs Certbot if it is not already installed.
- **Certificate Request**: Uses Certbot to obtain SSL certificates for the specified domain and its `www` subdomain.
- **Certificate Verification**: Verifies that the SSL certificates were successfully obtained.

### configure_apache.sh

`configure_apache.sh` handles the configuration of the Apache web server to serve the application over HTTPS. It includes the following tasks:

- **Apache Installation**: Installs Apache if it is not already installed.
- **Virtual Host Configuration**: Creates an Apache virtual host configuration for the specified domain, including SSL configuration if certificates are available.
- **Site Enabling**: Enables the new site configuration and reloads Apache to apply the changes.

## Running the Setup

To set up the environment, follow these steps:

1. **Ensure All Scripts Are in Place**: Make sure the following scripts are in the same directory:
   - `setup.sh`
   - `setup_variables.sh`
   - `configure_service.sh`
   - `configure_certbot.sh`
   - `configure_apache.sh`

2. **Make Scripts Executable**: Ensure all scripts have executable permissions:
   ```bash
   chmod +x setup.sh setup_variables.sh configure_service.sh configure_certbot.sh configure_apache.sh configure_python.sh
   ```

3. **Run the Setup Script**: Execute the `setup.sh` script to begin the setup process:
   ```bash
   sudo ./setup.sh
   ```

## Dependencies

The setup process requires the following dependencies:

- **Docker**: For containerizing the application.
- **Uvicorn**: ASGI server to run the Python application.
- **Certbot**: For obtaining SSL certificates.
- **Apache**: Web server for serving the application over HTTP/HTTPS.
- **Systemd**: For managing the Uvicorn service.

Ensure these dependencies are available on the system where the setup is being performed.

## Troubleshooting

- **Docker Installation Issues**: If Docker fails to install, ensure that the appropriate repositories are added to your package manager and that there are no conflicting installations.
- **Service Not Starting**: If the systemd service for Uvicorn does not start, check the logs using `sudo systemctl status <SERVICE_NAME>` to identify the issue.
- **SSL Certificate Issues**: If Certbot fails to obtain an SSL certificate, verify that the domain is correctly pointed to the server's IP address and that port 80 is open.
- **Apache Configuration Problems**: If Apache does not correctly serve the application, check the virtual host configuration and ensure that the SSL certificates are correctly referenced.

This documentation provides a comprehensive overview of the setup process, ensuring that all components are correctly configured and that the application is properly deployed and accessible.