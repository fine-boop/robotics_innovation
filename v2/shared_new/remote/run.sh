#!/bin/bash

# -----------------------------
# run.sh - Setup & run Flask app
# -----------------------------

# Exit immediately if a command fails
set -e

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root to bind to port 80."
    exit 1
fi

# Name of your virtual environment
VENV_DIR="venv"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv $VENV_DIR
fi

# Activate virtual environment
source $VENV_DIR/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install required packages
pip install flask gunicorn requests

# Create required directories if they don't exist
mkdir -p uploads downloads

# Run Gunicorn with 4 workers, binding to all interfaces on port 80
echo "Starting Gunicorn on port 80..."
gunicorn -w 4 -b 0.0.0.0:80 app:app --reload
