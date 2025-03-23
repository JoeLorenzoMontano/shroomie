#!/usr/bin/env python3
import os
from flask import Flask, render_template, request, jsonify
import sys
from shroomie.cli.main import main as shroomie_main
from shroomie.cli.cli_parser import CliParser
from io import StringIO
import json
import argparse
from shroomie.utils.map_generator import MapGenerator
from shroomie.utils.grid_utils import GridUtils
from shroomie.apis.soil_apis import SoilAPI
from shroomie.apis.location_apis import LocationAPI
from shroomie.apis.forest_apis import ForestAPI
from shroomie.apis.weather_apis import WeatherAPI

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

# Cache for API results to avoid redundant API calls
api_cache = {}

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
    
    # Create a cache key based on the arguments
    # This allows us to cache results for identical requests
    cache_key = str(sorted(args_dict.items()))
    
    # Check if we have cached results for this exact query
    if cache_key in api_cache:
        return api_cache[cache_key]
    
    # Capture stdout
    original_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    
    try:
        # Apply monkey patching to add caching to API calls
        # This helps speed up repeated API calls within the same session
        
        # Cache the original methods
        original_soil_properties = SoilAPI.get_soil_properties
        original_forest_cover = ForestAPI.get_forest_cover
        original_weather = WeatherAPI.get_weather_history
        
        # Create local caches
        soil_cache = {}
        forest_cache = {}
        weather_cache = {}
        
        # Create cached versions of slow API methods
        def cached_soil_properties(lat, lon, *args, **kwargs):
            cache_key = f"{lat}_{lon}"
            if cache_key not in soil_cache:
                soil_cache[cache_key] = original_soil_properties(lat, lon, *args, **kwargs)
            return soil_cache[cache_key]
        
        def cached_forest_cover(lat, lon, *args, **kwargs):
            cache_key = f"{lat}_{lon}"
            if cache_key not in forest_cache:
                forest_cache[cache_key] = original_forest_cover(lat, lon, *args, **kwargs)
            return forest_cache[cache_key]
        
        def cached_weather_history(lat, lon, *args, **kwargs):
            cache_key = f"{lat}_{lon}"
            if cache_key not in weather_cache:
                weather_cache[cache_key] = original_weather(lat, lon, *args, **kwargs)
            return weather_cache[cache_key]
        
        # Apply the monkey patches
        SoilAPI.get_soil_properties = cached_soil_properties
        ForestAPI.get_forest_cover = cached_forest_cover
        WeatherAPI.get_weather_history = cached_weather_history
        
        # Run the main function
        shroomie_main()
        output = mystdout.getvalue()
        
        # Cache the result
        api_cache[cache_key] = output
        
        # Restore original methods
        SoilAPI.get_soil_properties = original_soil_properties
        ForestAPI.get_forest_cover = original_forest_cover
        WeatherAPI.get_weather_history = original_weather
        
    except Exception as e:
        output = f"Error: {str(e)}"
    finally:
        # Reset stdout
        sys.stdout = original_stdout
    
    return output

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

def generate_map_html(lat, lon, zoom=10, include_soil_data=None, is_grid=False, grid_size=3, grid_distance=1.0):
    """Generate map HTML directly for embedding in the web page"""
    try:
        import folium
        
        if is_grid:
            # Calculate grid coordinates
            coordinates = GridUtils.calculate_grid_coordinates(lat, lon, grid_size, grid_distance)
            
            # Create a map centered at the original coordinates
            my_map = folium.Map(location=[lat, lon], zoom_start=zoom)
            
            # Organize grid points and find boundaries
            grid_points = {}
            min_lat = float('inf')
            max_lat = float('-inf')
            min_lon = float('inf')
            max_lon = float('-inf')
            
            # Group coordinates into a 2D grid structure for easier line drawing
            point_idx = 0
            for i in range(grid_size):
                for j in range(grid_size):
                    grid_lat, grid_lon = coordinates[point_idx]
                    if (i, j) not in grid_points:
                        grid_points[(i, j)] = (grid_lat, grid_lon)
                    
                    # Track boundaries
                    min_lat = min(min_lat, grid_lat)
                    max_lat = max(max_lat, grid_lat)
                    min_lon = min(min_lon, grid_lon)
                    max_lon = max(max_lon, grid_lon)
                    
                    point_idx += 1
            
            # Add grid lines (horizontal)
            for i in range(grid_size):
                points = []
                for j in range(grid_size):
                    grid_lat, grid_lon = grid_points[(i, j)]
                    points.append([grid_lat, grid_lon])
                
                folium.PolyLine(
                    locations=points,
                    color="blue",
                    weight=2,
                    opacity=0.7,
                    dash_array="5, 5"
                ).add_to(my_map)
            
            # Add grid lines (vertical)
            for j in range(grid_size):
                points = []
                for i in range(grid_size):
                    grid_lat, grid_lon = grid_points[(i, j)]
                    points.append([grid_lat, grid_lon])
                
                folium.PolyLine(
                    locations=points,
                    color="blue",
                    weight=2,
                    opacity=0.7,
                    dash_array="5, 5"
                ).add_to(my_map)
            
            # Add outline around the entire grid
            boundary_points = [
                [min_lat, min_lon],
                [min_lat, max_lon],
                [max_lat, max_lon],
                [max_lat, min_lon],
                [min_lat, min_lon]
            ]
            folium.PolyLine(
                locations=boundary_points,
                color="red",
                weight=3,
                opacity=0.9
            ).add_to(my_map)
            
            # Add markers for all grid points
            for idx, (grid_lat, grid_lon) in enumerate(coordinates):
                popup_content = f"Point {idx+1}: {grid_lat}, {grid_lon}"
                
                # Make the center point a different color
                if idx == len(coordinates) // 2:  # Center point in the grid
                    folium.Marker(
                        location=[grid_lat, grid_lon],
                        popup=popup_content,
                        tooltip="Center point",
                        icon=folium.Icon(color="red")
                    ).add_to(my_map)
                else:
                    folium.Marker(
                        location=[grid_lat, grid_lon],
                        popup=popup_content,
                        tooltip=f"Point {idx+1}"
                    ).add_to(my_map)
        else:
            # Create a map centered at the coordinates
            my_map = folium.Map(location=[lat, lon], zoom_start=zoom)
            
            # Prepare popup content
            popup_content = f"Coordinates: {lat}, {lon}"
            
            # Try to get location name
            try:
                location_data = LocationAPI.get_location_name(lat, lon)
                if location_data and "name" in location_data:
                    popup_content = f"{location_data['name']}<br>{popup_content}"
            except:
                pass
            
            # Get soil data if not provided
            if not include_soil_data:
                try:
                    include_soil_data = SoilAPI.get_soil_properties(lat, lon)
                except:
                    pass
            
            # Add soil data to popup if available
            if include_soil_data and "error" not in include_soil_data:
                popup_content += "<br><b>Soil Properties:</b><br>"
                
                try:
                    if "properties" in include_soil_data and "layers" in include_soil_data["properties"]:
                        layers = include_soil_data["properties"]["layers"]
                        
                        for layer in layers:
                            property_name = layer.get("name", layer.get("code", "Unknown"))
                            unit = layer.get("unit_measure", {}).get("target_units", "")
                            conversion = layer.get("unit_measure", {}).get("conversion_factor", 1)
                            
                            popup_content += f"<br><b>{property_name}</b>"
                            if unit:
                                popup_content += f" ({unit})"
                            popup_content += ":<br>"
                            
                            if "depths" in layer:
                                for depth in layer["depths"]:
                                    depth_label = depth.get("label", "Unknown depth")
                                    popup_content += f"&nbsp;&nbsp;{depth_label}: "
                                    
                                    if "values" in depth:
                                        values_str = []
                                        for stat, value in depth["values"].items():
                                            if conversion != 1:
                                                converted_value = value / conversion
                                                values_str.append(f"{stat}={converted_value:.1f}")
                                            else:
                                                values_str.append(f"{stat}={value}")
                                        
                                        popup_content += ", ".join(values_str)
                                    popup_content += "<br>"
                except Exception as e:
                    popup_content += f"<br>Error processing soil data: {str(e)}<br>"
            
            # Add a marker at the coordinates with the popup
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip="Click for soil data"
            ).add_to(my_map)
        
        # Return map HTML
        return my_map._repr_html_()
    except Exception as e:
        return f"<div class='alert alert-danger'>Error generating map: {str(e)}</div>"

from concurrent.futures import ThreadPoolExecutor
import time

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    start_time = time.time()
    
    # Process the input data
    args_dict = {}
    
    # Get coordinates
    lat = None
    lon = None
    
    if data.get('location'):
        args_dict['location'] = data['location']
        
        # Geocode the location
        try:
            location_result = LocationAPI.geocode_location(data['location'])
            if "error" not in location_result:
                lat = float(location_result["lat"])
                lon = float(location_result["lon"])
        except:
            pass
    elif data.get('lat') and data.get('lon'):
        lat = float(data['lat'])
        lon = float(data['lon'])
        args_dict['lat'] = lat
        args_dict['lon'] = lon
    else:
        return jsonify({'error': 'Either coordinates or location name required'})
    
    # Add other options
    is_grid = data.get('grid') == 'true'
    grid_size = int(data.get('grid-size', 3))
    grid_distance = float(data.get('grid-distance', 1.0))
    
    if is_grid:
        args_dict['grid'] = True
        args_dict['grid-size'] = grid_size
        args_dict['grid-distance'] = grid_distance
    
    # Use parallel processing for generating map and running data retrieval
    map_html = None
    output = None
    
    # Define functions for parallel execution
    def generate_map():
        if data.get('map') == 'true' and lat is not None and lon is not None:
            return generate_map_html(
                lat=lat, 
                lon=lon,
                zoom=10,
                is_grid=is_grid,
                grid_size=grid_size,
                grid_distance=grid_distance
            )
        return None
    
    def run_data_retrieval():
        # Always generate prompt (for readable output)
        args_dict['prompt'] = True
        
        # For grid mode, limit what we retrieve to speed things up
        if is_grid and grid_size > 3:
            # Skip soil properties for large grids as it's the slowest API
            args_dict['soil-properties'] = False
            
            # If it's a very large grid, further optimize
            if grid_size >= 5:
                args_dict['forest'] = False
        
        # Run Shroomie with optimized parameters
        return run_shroomie_with_args(args_dict)
    
    # Run map generation and data retrieval in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        map_future = executor.submit(generate_map)
        data_future = executor.submit(run_data_retrieval)
        
        # Get results
        map_html = map_future.result()
        output = data_future.result()
    
    # Calculate processing time
    processing_time = round(time.time() - start_time, 2)
    
    return jsonify({
        'output': output,
        'map_html': map_html,
        'processing_time': processing_time
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)