#!/usr/bin/env python3
import os
from flask import Flask, render_template, request, jsonify
import sys
import re
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
from shroomie.utils.prompt_generator import PromptGenerator

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

def extract_data_from_output(output_text):
    """
    Extract relevant data from the Shroomie output text to enhance map markers
    """
    data = {
        "location_name": "Unknown Location",
        "elevation": None,
        "tree_cover": None,
        "ecoregion": None,
        "forest_type": None,
        "dominant_trees": [],
        "mushroom_types": [],
        "soil_type": None,
        "soil_properties": {}
    }
    
    try:
        # Extract location name
        location_match = re.search(r"Location: (.+?)(?:\n|$)", output_text)
        if location_match:
            data["location_name"] = location_match.group(1).strip()
        
        # Extract elevation
        elevation_match = re.search(r"Elevation.*?: (\d+(?:\.\d+)?)", output_text)
        if elevation_match:
            data["elevation"] = float(elevation_match.group(1))
        
        # Extract tree cover
        tree_cover_match = re.search(r"Tree Cover: (\d+(?:\.\d+)?)%", output_text)
        if tree_cover_match:
            data["tree_cover"] = float(tree_cover_match.group(1))
        
        # Extract ecoregion
        ecoregion_match = re.search(r"Ecoregion: (.+?)(?:\n|$)", output_text)
        if ecoregion_match:
            data["ecoregion"] = ecoregion_match.group(1).strip()
        
        # Extract forest type
        forest_type_match = re.search(r"Forest Type: (.+?)(?:\n|$)", output_text)
        if forest_type_match:
            data["forest_type"] = forest_type_match.group(1).strip()
        
        # Extract dominant tree species
        tree_section = re.search(r"Dominant Tree Species:(.*?)(?:\n\n|\n[^*\s])", output_text, re.DOTALL)
        if tree_section:
            trees = re.findall(r"\*\s+(.+?)(?:\n|$)", tree_section.group(1))
            data["dominant_trees"] = [tree.strip() for tree in trees]
        
        # Extract mushroom associations
        mushroom_section = re.search(r"Mushroom-Tree Associations:(.*?)(?:\n\n|\n[^-\s])", output_text, re.DOTALL)
        if mushroom_section:
            mushroom_lines = re.findall(r"-\s+.+?:\s+(.+?)(?:\n|$)", mushroom_section.group(1))
            for line in mushroom_lines:
                mushrooms = [m.strip() for m in line.split(',')]
                data["mushroom_types"].extend(mushrooms)
            # Remove duplicates while preserving order
            seen = set()
            data["mushroom_types"] = [m for m in data["mushroom_types"] if not (m in seen or seen.add(m))]
        
        # Extract soil type
        soil_type_match = re.search(r"Primary Soil Type.*?: (.+?)(?:\n|$)", output_text)
        if soil_type_match:
            data["soil_type"] = soil_type_match.group(1).strip()
        
        # Extract soil properties
        soil_section = re.search(r"Soil Properties:(.*?)(?:\n\n|\n[^*\s])", output_text, re.DOTALL)
        if soil_section:
            properties = re.findall(r"\*\s+(.+?)(?:\n|$)", soil_section.group(1))
            for prop in properties:
                if ':' in prop:
                    name, value = prop.split(':', 1)
                    data["soil_properties"][name.strip()] = value.strip()
                else:
                    data["soil_properties"][prop.strip()] = "No specific value"
        
        return data
    except Exception as e:
        print(f"Error extracting data from output: {str(e)}")
        return data

def calculate_species_suitability(lat, lon, species_list, environmental_data=None):
    """
    Calculate suitability scores for specified mushroom species.

    Args:
        lat: Latitude
        lon: Longitude
        species_list: List of species IDs to analyze
        environmental_data: Optional pre-fetched environmental data

    Returns:
        Dict with species scores and details
    """
    try:
        from shroomie.data.species_loader import SpeciesDatabase
        from shroomie.utils.suitability_scorer import SuitabilityScorer
        from shroomie.apis.soil_apis import SoilAPI
        from shroomie.apis.location_apis import ElevationAPI
        from shroomie.apis.forest_apis import ForestAPI
        from shroomie.apis.weather_apis import WeatherAPI

        # Gather environmental data if not provided
        if environmental_data is None:
            environmental_data = {}

            # Get soil pH (from soil properties)
            try:
                soil_props = SoilAPI.get_soil_properties(lat, lon)
                if soil_props and not soil_props.get('error'):
                    # Extract pH from soil properties
                    layers = soil_props.get('properties', {}).get('layers', [])
                    for layer in layers:
                        if layer.get('name') == 'phh2o':
                            depths = layer.get('depths', [])
                            if depths:
                                ph_value = depths[0].get('values', {}).get('mean')
                                if ph_value:
                                    environmental_data['soil_ph'] = ph_value / 10.0  # Convert from pH*10 to pH
                                    break
            except Exception as e:
                print(f"Error getting soil pH: {e}")

            # Get elevation
            try:
                elev_data = ElevationAPI.get_elevation_data(lat, lon)
                if elev_data and not elev_data.get('error'):
                    environmental_data['elevation'] = elev_data.get('elevation', 0)
            except Exception as e:
                print(f"Error getting elevation: {e}")

            # Get tree species
            try:
                tree_data = ForestAPI.get_tree_species(lat, lon)
                if tree_data and not tree_data.get('error'):
                    dominant = tree_data.get('dominant_species', [])
                    environmental_data['dominant_trees'] = dominant
            except Exception as e:
                print(f"Error getting tree species: {e}")
                environmental_data['dominant_trees'] = []

            # Get weather data
            try:
                weather_data = WeatherAPI.get_weather_history(lat, lon, months=1)
                if weather_data and not weather_data.get('error'):
                    monthly_avgs = weather_data.get('monthly_averages', {})
                    if monthly_avgs:
                        latest_month = list(monthly_avgs.values())[-1]
                        environmental_data['temperature_mean'] = latest_month.get('temp_mean', 15)
                        environmental_data['precipitation'] = latest_month.get('precip_sum', 50)
            except Exception as e:
                print(f"Error getting weather: {e}")

        # Calculate scores for each species
        species_db = SpeciesDatabase()
        results = {}

        print(f"🍄 Calculating scores for species: {species_list}")
        print(f"📊 Environmental data available: {list(environmental_data.keys())}")

        for species_id in species_list:
            try:
                species_data = species_db.get_species(species_id)
                if species_data:
                    scorer = SuitabilityScorer(species_data)
                    score_result = scorer.calculate_score(environmental_data)
                    results[species_id] = {
                        'common_name': species_data.get('common_name', species_id),
                        'score': score_result['overall_score'],
                        'factor_scores': score_result['factor_scores'],
                        'details': score_result.get('details', {})
                    }
                    print(f"✓ Scored {species_data.get('common_name')}: {score_result['overall_score']}")
                else:
                    print(f"✗ Species not found: {species_id}")
            except Exception as e:
                print(f"✗ Error scoring {species_id}: {str(e)}")
                import traceback
                traceback.print_exc()

        # Sort by score descending
        sorted_results = dict(sorted(results.items(), key=lambda x: x[1]['score'], reverse=True))

        return {
            'species_scores': sorted_results,
            'environmental_data': environmental_data
        }

    except Exception as e:
        return {
            'error': f"Error calculating suitability: {str(e)}",
            'species_scores': {},
            'environmental_data': {}
        }

def find_best_spots(center_lat, center_lon, radius_miles, species_id, min_score=60, top_n=10):
    """
    Scan an area to find the best locations for a mushroom species.

    Args:
        center_lat: Center latitude
        center_lon: Center longitude
        radius_miles: Search radius in miles
        species_id: Species identifier to search for
        min_score: Minimum suitability score (0-100)
        top_n: Number of top locations to return

    Returns:
        List of dicts with location data sorted by score descending
        Format: [{'lat': 45.1, 'lon': -123.5, 'score': 85.2, 'factor_scores': {...}}, ...]
    """
    try:
        from shroomie.utils.grid_utils import GridUtils
        from shroomie.data.species_loader import SpeciesDatabase

        print(f"🔍 Finding best spots for {species_id} within {radius_miles} miles...")

        # Calculate grid size based on radius
        # Use smaller grid spacing for smaller radius, larger for bigger radius
        if radius_miles <= 5:
            grid_size = 10
            grid_distance = radius_miles / 5.0  # ~0.5-1 mile spacing
        elif radius_miles <= 10:
            grid_size = 12
            grid_distance = radius_miles / 6.0  # ~1-2 mile spacing
        else:
            grid_size = 15
            grid_distance = radius_miles / 7.5  # ~2-3 mile spacing

        # Generate grid coordinates
        coordinates = GridUtils.calculate_grid_coordinates(
            center_lat, center_lon, grid_size, grid_distance
        )

        print(f"📍 Scanning {len(coordinates)} locations...")

        # Calculate suitability score for each point
        results = []
        for idx, (lat, lon) in enumerate(coordinates):
            try:
                scoring_result = calculate_species_suitability(lat, lon, [species_id])

                if scoring_result and scoring_result.get('species_scores'):
                    species_data = scoring_result['species_scores'].get(species_id)

                    if species_data and species_data['score'] >= min_score:
                        results.append({
                            'lat': lat,
                            'lon': lon,
                            'score': species_data['score'],
                            'factor_scores': species_data.get('factor_scores', {}),
                            'common_name': species_data.get('common_name', species_id)
                        })

                # Progress indicator every 25 points
                if (idx + 1) % 25 == 0:
                    print(f"  ... processed {idx + 1}/{len(coordinates)} points")

            except Exception as e:
                # Skip failed points
                continue

        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)

        # Return top N
        top_results = results[:top_n]

        print(f"✓ Found {len(results)} suitable locations (showing top {len(top_results)})")

        # Add ranking
        for rank, result in enumerate(top_results, 1):
            result['rank'] = rank

        return top_results

    except Exception as e:
        print(f"✗ Error in find_best_spots: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def generate_map_html(lat, lon, zoom=10, include_soil_data=None, is_grid=False, grid_size=3, grid_distance=1.0, enhanced_data=None, species_scores=None):
    """Generate map HTML directly for embedding in the web page

    Args:
        species_scores: Dict mapping (lat, lon) tuples to species score data
                       Format: {(lat, lon): {'species_id': {'score': 75.5, 'common_name': 'Morels'}, ...}}
    """
    try:
        import folium
        from folium.plugins import FastMarkerCluster, HeatMap
        import numpy as np
        
        # Create a map with optimized settings
        if is_grid:
            # Use exactly the same initialization as single point mode
            # Default to OpenStreetMap tiles which is Folium's default
            my_map = folium.Map(
                location=[lat, lon],
                zoom_start=zoom,
                control_scale=True,
                tiles='OpenStreetMap',  # Explicitly set to match single point default
                prefer_canvas=True  # Use canvas renderer for better performance
            )
            
            # Calculate grid coordinates
            coordinates = GridUtils.calculate_grid_coordinates(lat, lon, grid_size, grid_distance)
            
            # Find boundaries quickly with numpy
            coords_array = np.array(coordinates)
            min_lat, max_lat = np.min(coords_array[:,0]), np.max(coords_array[:,0])
            min_lon, max_lon = np.min(coords_array[:,1]), np.max(coords_array[:,1])
            
            # Create a Feature Group for better performance
            grid_lines = folium.FeatureGroup(name="Grid", show=True)
            
            # For larger grids, simplify rendering
            if grid_size <= 5:
                # Create organized grid structure for smaller grids
                grid_points = {}
                for idx, (grid_lat, grid_lon) in enumerate(coordinates):
                    i, j = idx // grid_size, idx % grid_size
                    grid_points[(i, j)] = (grid_lat, grid_lon)
                
                # Add horizontal and vertical lines
                for i in range(grid_size):
                    h_points = [[grid_points[(i, j)][0], grid_points[(i, j)][1]] for j in range(grid_size)]
                    folium.PolyLine(
                        locations=h_points,
                        color="blue",
                        weight=2,
                        opacity=0.7,
                        dash_array="5, 5"
                    ).add_to(grid_lines)
                
                for j in range(grid_size):
                    v_points = [[grid_points[(i, j)][0], grid_points[(i, j)][1]] for i in range(grid_size)]
                    folium.PolyLine(
                        locations=v_points,
                        color="blue",
                        weight=2,
                        opacity=0.7,
                        dash_array="5, 5"
                    ).add_to(grid_lines)
            else:
                # For larger grids (>5x5), only draw boundary and omit internal grid lines
                folium.Rectangle(
                    bounds=[[min_lat, min_lon], [max_lat, max_lon]],
                    color='blue',
                    weight=2,
                    fill=True,
                    fill_color='blue',
                    fill_opacity=0.05,
                    dash_array="5, 5"
                ).add_to(grid_lines)
            
            # Add grid outline
            folium.Rectangle(
                bounds=[[min_lat, min_lon], [max_lat, max_lon]],
                color='red',
                weight=3,
                fill=False
            ).add_to(grid_lines)
            
            # Add the grid lines to the map
            grid_lines.add_to(my_map)

            # Add heatmap layers if species scores are available
            if species_scores:
                from shroomie.utils.heatmap_generator import HeatmapGenerator

                # Organize scores by species
                species_heatmaps = {}
                for coord, scores_dict in species_scores.items():
                    for species_id, score_data in scores_dict.items():
                        if species_id not in species_heatmaps:
                            species_heatmaps[species_id] = {
                                'common_name': score_data.get('common_name', species_id),
                                'scores': {}
                            }
                        species_heatmaps[species_id]['scores'][coord] = score_data['score']

                # Create a heatmap layer for each species
                for species_id, heatmap_info in species_heatmaps.items():
                    grid_scores = heatmap_info['scores']
                    common_name = heatmap_info['common_name']

                    # Generate interpolated heatmap data
                    heat_data = HeatmapGenerator.interpolate_grid_scores(
                        grid_scores,
                        resolution=20
                    )

                    if heat_data:
                        # Create heatmap layer
                        HeatMap(
                            heat_data,
                            name=f"{common_name} Suitability",
                            gradient={
                                0.0: 'red',
                                0.25: 'orange',
                                0.5: 'yellow',
                                0.75: 'lightgreen',
                                1.0: 'green'
                            },
                            min_opacity=0.3,
                            max_opacity=0.8,
                            radius=25,
                            blur=35,
                            show=True  # Show first species by default
                        ).add_to(my_map)

                # Also add colored circle markers for each grid point
                for coord, scores_dict in species_scores.items():
                    grid_lat, grid_lon = coord

                    # Use the highest scoring species for the marker color
                    best_species = max(scores_dict.items(), key=lambda x: x[1]['score'])
                    best_score = best_species[1]['score']
                    best_name = best_species[1]['common_name']

                    # Create popup with all species scores
                    popup_html = f"""
                    <div style="font-family: Arial; min-width: 220px;">
                        <h5 style="margin: 0 0 10px 0; border-bottom: 1px solid #ddd; padding-bottom: 5px;">
                            Grid Point: {grid_lat:.4f}, {grid_lon:.4f}
                        </h5>
                        <p style="margin: 5px 0;"><strong>Species Suitability Scores:</strong></p>
                        <table style="width: 100%; font-size: 12px;">
                    """

                    # Sort species by score descending
                    sorted_species = sorted(scores_dict.items(), key=lambda x: x[1]['score'], reverse=True)
                    for species_id, score_data in sorted_species:
                        score = score_data['score']
                        name = score_data['common_name']
                        color = HeatmapGenerator.create_color_gradient(score)
                        popup_html += f"""
                            <tr>
                                <td style="padding: 3px;">{name}:</td>
                                <td style="padding: 3px; text-align: right;">
                                    <span style="background-color: {color}; padding: 2px 6px; border-radius: 3px; color: white; font-weight: bold;">
                                        {score:.1f}
                                    </span>
                                </td>
                            </tr>
                        """

                    popup_html += "</table></div>"

                    # Create circle marker with color based on best score
                    marker = HeatmapGenerator.create_circle_marker(
                        grid_lat, grid_lon, best_score, best_name,
                        popup_data=None  # We're using custom popup
                    )

                    # Replace the popup with our multi-species version
                    marker.popup = folium.Popup(popup_html, max_width=300)
                    marker.add_to(my_map)

            # Optimize marker rendering based on grid size
            if grid_size <= 6:  # Standard marker display for smaller grids
                # Create a feature group for markers
                markers = folium.FeatureGroup(name="Points")
                
                # Find center point index
                center_idx = len(coordinates) // 2
                
                # For smaller grids, use standard markers
                # Just use a single red marker for center and simple dot markers for others
                for idx, (grid_lat, grid_lon) in enumerate(coordinates):
                    popup_content = f"Point {idx+1}: {grid_lat:.5f}, {grid_lon:.5f}"
                    
                    if idx == center_idx:
                        # Center point as red marker
                        folium.Marker(
                            location=[grid_lat, grid_lon],
                            popup=popup_content,
                            tooltip="Center point",
                            icon=folium.Icon(color="red", icon="star"),
                        ).add_to(markers)
                    else:
                        # Use CircleMarker instead of Marker for better performance
                        folium.CircleMarker(
                            location=[grid_lat, grid_lon],
                            radius=4,
                            popup=popup_content,
                            tooltip=f"Point {idx+1}",
                            color="blue",
                            fill=True,
                            fill_color="blue",
                            fill_opacity=0.7,
                        ).add_to(markers)
                
                markers.add_to(my_map)
            
            else:
                # For very large grids (>6x6), use cluster markers for better performance
                # Prepare callback for cluster markers
                callback = """
                    function (row) {
                        var icon, size;
                        if (row[2] === 1) {  // Center point
                            icon = L.divIcon({
                                html: '<div style="background-color: #e74c3c; width: 10px; height: 10px; border-radius: 50%;"></div>',
                                className: 'marker-cluster',
                                iconSize: L.point(10, 10)
                            });
                        } else {
                            icon = L.divIcon({
                                html: '<div style="background-color: #3498db; width: 6px; height: 6px; border-radius: 50%;"></div>',
                                className: 'marker-cluster',
                                iconSize: L.point(6, 6)
                            });
                        }
                        return L.marker(new L.LatLng(row[0], row[1]), {icon: icon});
                    };
                """
                
                # Prepare data for fast marker cluster
                marker_data = []
                center_idx = len(coordinates) // 2
                
                for idx, (grid_lat, grid_lon) in enumerate(coordinates):
                    is_center = 1 if idx == center_idx else 0
                    marker_data.append([grid_lat, grid_lon, is_center])
                
                # Use FastMarkerCluster for efficient rendering of many points
                FastMarkerCluster(
                    data=marker_data,
                    callback=callback,
                    name="Grid Points",
                    options={'maxClusterRadius': 1}  # Small radius so points aren't clustered
                ).add_to(my_map)
            
            # Add layer control if we have species heatmaps
            if species_scores:
                folium.LayerControl(collapsed=False).add_to(my_map)

            # Fit map to bounds
            my_map.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])
            
        else:
            # Single point map with default OpenStreetMap tiles
            my_map = folium.Map(
                location=[lat, lon],
                zoom_start=zoom,
                control_scale=True,
                tiles='OpenStreetMap'  # Explicitly set to ensure consistency
            )
            
            # Create enhanced popup content from the extracted data
            if enhanced_data:
                popup_html = f"""
                <div style="font-family: Arial, sans-serif; max-width: 400px;">
                    <h4 style="color: #336699; margin-bottom: 8px; border-bottom: 1px solid #ddd; padding-bottom: 5px;">
                        Location Analysis
                    </h4>
                    
                    <div style="margin-bottom: 10px;">
                        <strong>{enhanced_data.get('location_name', 'Unknown Location')}</strong><br>
                        <span style="color: #666;">Coordinates: {lat:.5f}, {lon:.5f}</span>
                    </div>
                """
                
                # Add elevation data if available
                if enhanced_data.get('elevation'):
                    popup_html += f"""
                    <div style="margin-bottom: 10px;">
                        <strong>Elevation:</strong> {enhanced_data['elevation']} meters
                    </div>
                    """
                
                # Add forest data if available
                if enhanced_data.get('tree_cover'):
                    popup_html += f"""
                    <div style="margin-bottom: 10px;">
                        <strong>Tree Cover:</strong> {enhanced_data['tree_cover']}%
                    </div>
                    """
                
                # Add ecoregion and forest type if available
                if enhanced_data.get('ecoregion') or enhanced_data.get('forest_type'):
                    popup_html += "<div style='margin-bottom: 10px;'>"
                    if enhanced_data.get('ecoregion'):
                        popup_html += f"<strong>Ecoregion:</strong> {enhanced_data['ecoregion']}<br>"
                    if enhanced_data.get('forest_type'):
                        popup_html += f"<strong>Forest Type:</strong> {enhanced_data['forest_type']}"
                    popup_html += "</div>"
                
                # Add dominant trees if available
                if enhanced_data.get('dominant_trees'):
                    popup_html += f"""
                    <div style="margin-bottom: 10px;">
                        <strong>Dominant Trees:</strong><br>
                        <ul style="margin: 5px 0 5px 20px; padding: 0;">
                    """
                    for tree in enhanced_data['dominant_trees'][:3]:  # Limit to top 3
                        popup_html += f"<li>{tree}</li>"
                    popup_html += "</ul></div>"
                
                # Add mushroom associations if available
                if enhanced_data.get('mushroom_types'):
                    popup_html += f"""
                    <div style="margin-bottom: 10px;">
                        <strong>Potential Mushroom Types:</strong><br>
                        <ul style="margin: 5px 0 5px 20px; padding: 0;">
                    """
                    for mushroom in enhanced_data['mushroom_types'][:5]:  # Limit to top 5
                        popup_html += f"<li>{mushroom}</li>"
                    popup_html += "</ul></div>"
                
                # Add soil type if available
                if enhanced_data.get('soil_type'):
                    popup_html += f"""
                    <div style="margin-bottom: 10px;">
                        <strong>Primary Soil Type:</strong> {enhanced_data['soil_type']}
                    </div>
                    """
                
                # Add soil properties if available
                if enhanced_data.get('soil_properties') and len(enhanced_data['soil_properties']) > 0:
                    popup_html += f"""
                    <div style="margin-bottom: 10px;">
                        <strong>Soil Properties:</strong><br>
                        <ul style="margin: 5px 0 5px 20px; padding: 0;">
                    """
                    for prop, value in list(enhanced_data['soil_properties'].items())[:3]:  # Limit to top 3
                        popup_html += f"<li>{prop}: {value}</li>"
                    popup_html += "</ul></div>"
                
                # Close container div
                popup_html += "</div>"
                
                # Add marker with enhanced popup
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_html, max_width=400),
                    tooltip="Click for detailed analysis",
                    icon=folium.Icon(color="green", icon="info-sign")
                ).add_to(my_map)
            else:
                # Fallback to basic marker if no enhanced data
                popup_content = f"Coordinates: {lat:.5f}, {lon:.5f}"
                folium.Marker(
                    location=[lat, lon],
                    popup=popup_content,
                    tooltip="Location"
                ).add_to(my_map)
        
        # Use minimal HTML generation
        html = my_map._repr_html_()
        
        # Remove some unnecessary meta tags from Folium output to reduce size
        html = html.replace('charset="utf-8"', 'charset="utf-8" loading="lazy"')
        
        return html
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

    # Get species selection
    species_list = data.get('species', [])
    if isinstance(species_list, str):
        species_list = [species_list]

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
    
    # Run data retrieval first
    output = run_data_retrieval()
    
    # Extract data from output for map enhancement
    map_data = extract_data_from_output(output)

    # Calculate species suitability scores if species selected
    species_scores = None
    grid_species_scores = None  # For heatmap visualization

    if species_list and lat is not None and lon is not None:
        if is_grid:
            # Calculate scores for all grid points
            from shroomie.utils.grid_utils import GridUtils

            coordinates = GridUtils.calculate_grid_coordinates(lat, lon, grid_size, grid_distance)
            grid_species_scores = {}

            print(f"🗺️  Calculating scores for {len(coordinates)} grid points...")

            # Calculate scores for each grid point
            for grid_lat, grid_lon in coordinates:
                coord_key = (grid_lat, grid_lon)
                scoring_result = calculate_species_suitability(grid_lat, grid_lon, species_list)

                if scoring_result and scoring_result.get('species_scores'):
                    grid_species_scores[coord_key] = scoring_result['species_scores']

            print(f"✓ Completed scoring for {len(grid_species_scores)} points")
        else:
            # Single point scoring
            scoring_result = calculate_species_suitability(lat, lon, species_list)
            species_scores = scoring_result.get('species_scores', {})

    # Find best spots mode
    best_spots_results = None
    if data.get('find_best_spots') == 'true' and species_list and lat is not None and lon is not None:
        # Get parameters
        search_radius = float(data.get('search_radius', 10))  # miles
        min_suitability = float(data.get('min_suitability', 60))  # 0-100
        top_n = int(data.get('top_n', 10))

        # Use first selected species for best spots search
        target_species = species_list[0]

        # Find best spots
        best_spots_results = find_best_spots(
            center_lat=lat,
            center_lon=lon,
            radius_miles=search_radius,
            species_id=target_species,
            min_score=min_suitability,
            top_n=top_n
        )

    # Then generate map with the data
    if data.get('map') == 'true' and lat is not None and lon is not None:
        map_html = generate_map_html(
            lat=lat,
            lon=lon,
            zoom=10,
            is_grid=is_grid,
            grid_size=grid_size,
            grid_distance=grid_distance,
            enhanced_data=map_data,  # Pass the extracted data
            species_scores=grid_species_scores if is_grid else None  # Pass grid scores for heatmap
        )
    else:
        map_html = None
    
    # Calculate processing time
    processing_time = round(time.time() - start_time, 2)

    # Prepare response
    response = {
        'output': output,
        'map_html': map_html,
        'species_scores': species_scores if not is_grid else None,
        'grid_species_scores': grid_species_scores if is_grid else None,
        'best_spots': best_spots_results,
        'processing_time': processing_time
    }

    # Add summary of grid results if available
    if grid_species_scores and species_list:
        summary = {}
        for species_id in species_list:
            scores = []
            for coord_scores in grid_species_scores.values():
                if species_id in coord_scores:
                    scores.append(coord_scores[species_id]['score'])

            if scores:
                summary[species_id] = {
                    'common_name': grid_species_scores[list(grid_species_scores.keys())[0]][species_id]['common_name'],
                    'avg_score': round(sum(scores) / len(scores), 1),
                    'max_score': round(max(scores), 1),
                    'min_score': round(min(scores), 1)
                }
        response['grid_summary'] = summary

    return jsonify(response)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)