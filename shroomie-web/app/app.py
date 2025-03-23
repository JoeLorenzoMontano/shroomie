#!/usr/bin/env python3
import os
from flask import Flask, render_template, request, jsonify
import sys
from shroomie.cli.main import main as shroomie_main
from shroomie.cli.cli_parser import CliParser
from io import StringIO
import json
import argparse

app = Flask(__name__)

# Custom ArgumentParser that doesn't exit on error
class WebArgumentParser(argparse.ArgumentParser):
    def exit(self, status=0, message=None):
        if message:
            self._exit_message = message
        raise Exception(message)

    def error(self, message):
        self.exit(2, message)

# Override the CliParser's create_parser method
def create_web_parser():
    parser = WebArgumentParser(description="Query environmental APIs and generate LLM prompts")
    
    # Coordinates and location
    location_group = parser.add_argument_group("Location Options")
    location_group.add_argument("--lat", type=float, help="Latitude")
    location_group.add_argument("--lon", type=float, help="Longitude")
    location_group.add_argument("--location", type=str, help="Location name to geocode")
    
    # Other arguments as needed for the web interface
    parser.add_argument("--prompt", action="store_true", help="Generate LLM prompt")
    parser.add_argument("--grid", action="store_true", help="Generate a grid of points")
    parser.add_argument("--grid-size", type=int, default=3, help="Size of the grid (e.g., 3 for a 3x3 grid)")
    parser.add_argument("--grid-distance", type=float, default=1.0, help="Distance between grid points in miles")
    
    return parser

# Capture stdout when running the Shroomie CLI
def run_shroomie_with_args(args_dict):
    # Prepare arguments
    sys.argv = ['shroomie']
    for key, value in args_dict.items():
        if value is not None:
            if isinstance(value, bool) and value is True:
                sys.argv.append(f"--{key}")
            elif not isinstance(value, bool):
                sys.argv.append(f"--{key}")
                sys.argv.append(str(value))
    
    # Capture stdout
    original_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    
    try:
        # Run the main function
        shroomie_main()
        output = mystdout.getvalue()
    except Exception as e:
        output = f"Error: {str(e)}"
    finally:
        # Reset stdout
        sys.stdout = original_stdout
    
    return output

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    
    # Process the input data
    args_dict = {}
    
    # Handle coordinates or location name
    if data.get('location'):
        args_dict['location'] = data['location']
    elif data.get('lat') and data.get('lon'):
        args_dict['lat'] = float(data['lat'])
        args_dict['lon'] = float(data['lon'])
    else:
        return jsonify({'error': 'Either coordinates or location name required'})
    
    # Add other options
    if data.get('grid') == 'true':
        args_dict['grid'] = True
        args_dict['grid-size'] = int(data.get('grid-size', 3))
        args_dict['grid-distance'] = float(data.get('grid-distance', 1.0))
    
    # Always generate prompt (for readable output)
    args_dict['prompt'] = True
    
    # Run Shroomie
    output = run_shroomie_with_args(args_dict)
    
    return jsonify({'output': output})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)