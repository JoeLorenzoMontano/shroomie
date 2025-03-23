#!/bin/sh
set -e

# Install the shroomie package from the mounted volume
pip install -e /shroomie

# Start the Flask application
python app.py