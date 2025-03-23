#!/bin/bash
set -e

# Install the shroomie package from the mounted volume
pip install -e /shroomie

# Start the Flask application
exec python app.py