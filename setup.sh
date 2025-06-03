#!/bin/bash
# Setup script for BMP-editor
set -e

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

echo "Setup complete. Activate the venv with 'source venv/bin/activate' and run 'python bmpapp.py'"
