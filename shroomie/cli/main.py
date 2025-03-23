#!/usr/bin/env python3
import sys
import json
from typing import Dict, Any, List, Optional, Union, Tuple
import os
from dotenv import load_dotenv

from shroomie.cli.cli_parser import CliParser
from shroomie.apis.soil_apis import SoilAPI
from shroomie.apis.location_apis import LocationAPI, ElevationAPI
from shroomie.apis.forest_apis import ForestAPI
from shroomie.apis.weather_apis import WeatherAPI
from shroomie.utils.grid_utils import GridUtils
from shroomie.utils.prompt_generator import PromptGenerator
from shroomie.utils.map_generator import MapGenerator
from shroomie.models.coordinate import Coordinate
from shroomie.models.soil_data import SoilData

def main() -> None:
    """Main entry point for the Shroomie CLI application."""
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Parse arguments
    args = CliParser.parse_arguments()
    
    # Validate arguments
    is_valid, error_message = CliParser.validate_arguments(args)
    if not is_valid:
        print(f"Error: {error_message}")
        return
    
    # Process coordinates
    coordinates = []
    
    # Check if we need to geocode a location name
    if not args.lat or not args.lon:
        if args.location:
            # Try to geocode the location
            location_result = LocationAPI.geocode_location(args.location)
            if "error" not in location_result:
                try:
                    args.lat = float(location_result["lat"])
                    args.lon = float(location_result["lon"])
                    print(f"Geocoded '{args.location}' to: Latitude {args.lat}, Longitude {args.lon}")
                except (KeyError, ValueError):
                    print(f"Error: Could not extract coordinates from geocoding result")
                    return
            else:
                print(f"Error: {location_result['error']}")
                return
    
    # Check if we need to generate a grid
    if args.grid:
        coordinates = GridUtils.calculate_grid_coordinates(args.lat, args.lon, args.grid_size, args.grid_distance)
        print(f"Generated a {args.grid_size}x{args.grid_size} grid with {len(coordinates)} points")
    else:
        # Just use the single coordinate provided
        coordinates = [(args.lat, args.lon)]
    
    # Process each coordinate
    for idx, (lat, lon) in enumerate(coordinates):
        if len(coordinates) > 1:
            print(f"\n{'='*20} Point {idx+1}/{len(coordinates)} (Lat: {lat}, Lon: {lon}) {'='*20}\n")
        
        openepi_result = None
        soilgrids_result = None
        elevation_result = None
        forest_result = None
        topo_result = None
        location_data = None
        weather_result = None
        soil_properties_result = None
        tree_species_result = None
        
        # Always get OpenStreetMap location data when coordinates are provided
        location_data = LocationAPI.get_location_name(lat, lon)
        if not args.prompt and (args.all or args.osm):
            print("===== OpenStreetMap Location Data =====")
            print(json.dumps(location_data, indent=2))
        
        # Determine if we should use defaults for mushroom foraging
        # If no specific data flags are set, use defaults for foraging
        use_defaults = not any([
            args.all, args.soilgrids, args.openepi, args.soil_properties, 
            args.elevation, args.topo, args.forest, args.trees, args.weather
        ])
        
        # Get weather data by default or if requested
        if args.all or args.weather or use_defaults:
            weather_result = WeatherAPI.get_weather_history(lat, lon, args.months)
            if not args.prompt:
                # For raw display, we'll show a simpler version without all the daily data
                display_weather = weather_result.copy() if isinstance(weather_result, dict) else {}
                if "daily" in display_weather:
                    # Remove the bulky daily data arrays to make the output cleaner
                    del display_weather["daily"]
                
                print("\n===== Historical Weather Data =====")
                print(json.dumps(display_weather, indent=2))
        
        # Get SoilGrids data by default or if requested
        if args.all or args.soilgrids or use_defaults or (not args.all and not args.openepi and not args.soil_properties):
            soilgrids_result = SoilAPI.get_soilgrids_data(lat, lon, args.number_classes)
            if not args.prompt:
                print("\n===== ISRIC SoilGrids API Result =====")
                print(json.dumps(soilgrids_result, indent=2))
        
        # Get OpenEPI soil type data by default or if requested
        if args.all or args.openepi or use_defaults:
            openepi_result = SoilAPI.get_soil_type(lat, lon, args.top_k)
            if not args.prompt:
                print("\n===== OpenEPI Soil Type API Result =====")
                print(json.dumps(openepi_result, indent=2))
        
        # Get soil property data by default or if requested
        if args.soil_properties or args.all or use_defaults:
            # If using defaults, set default values for properties, depths, and values if not provided
            depths = args.depths if args.depths else ["0-5cm"]
            properties = args.properties if args.properties else ["bdod", "phh2o"]
            values = args.values if args.values else ["mean", "Q0.05"]
            
            soil_properties_result = SoilAPI.get_soil_properties(lat, lon, depths, properties, values)
            if not args.prompt:
                print("\n===== OpenEPI Soil Properties API Result =====")
                print(json.dumps(soil_properties_result, indent=2))
        
        # Get elevation data by default or if requested
        if args.all or args.elevation or use_defaults:
            elevation_result = ElevationAPI.get_elevation_data(lat, lon)
            if not args.prompt:
                print("\n===== Open-Elevation API Result =====")
                print(json.dumps(elevation_result, indent=2))
        
        # Get topographic data by default or if requested
        if args.all or args.topo or use_defaults:
            topo_result = ElevationAPI.get_open_topo_data(lat, lon)
            if not args.prompt:
                print("\n===== Open-Meteo Topographic API Result =====")
                print(json.dumps(topo_result, indent=2))
        
        # Get forest cover data by default or if requested
        if args.all or args.forest or use_defaults:
            forest_result = ForestAPI.get_forest_cover(lat, lon, args.gfw_api_key)
            if not args.prompt:
                print("\n===== Global Forest Watch API Result =====")
                print(json.dumps(forest_result, indent=2))
        
        # Get tree species data by default or if requested
        if args.all or args.trees or use_defaults:
            tree_species_result = ForestAPI.get_tree_species(lat, lon)
            if not args.prompt:
                print("\n===== Tree Species Data =====")
                print(json.dumps(tree_species_result, indent=2))
        
        # Generate and output LLM prompt by default or if requested
        if args.prompt or use_defaults:
            prompt = PromptGenerator.generate_llm_prompt(
                openepi_data=openepi_result, 
                soilgrids_data=soilgrids_result,
                elevation_data=elevation_result,
                forest_data=forest_result,
                topo_data=topo_result,
                weather_data=weather_result,
                tree_data=tree_species_result,
                soil_properties_data=soil_properties_result,
                mushroom_type=args.mushroom_type,
                location_name=args.location_name,
                location_data=location_data,
                lat=lat,
                lon=lon
            )
            print(prompt)
            
            # Add a separator between grid points if we're processing multiple points
            if len(coordinates) > 1 and idx < len(coordinates) - 1:
                print("\n" + "="*80 + "\n")
        
        # Generate an interactive map if requested
        if args.map and not args.grid:  # Only generate individual maps if not grid mode
            try:
                # Generate the map with soil property data if available
                map_file = MapGenerator.generate_map(
                    lat=lat,
                    lon=lon,
                    zoom=args.map_zoom,
                    output_file=args.map_output,
                    include_soil_data=soil_properties_result
                )
                
                if map_file:
                    print(f"\nMap has been generated at: {map_file}")
                    print(f"Open the file in a web browser to view the interactive map.")
                
            except Exception as e:
                print(f"\nError generating map: {str(e)}")
                print("Make sure you have folium installed (pip install folium)")
                print("To install folium, run: pip install folium")
    
    # Generate a combined map with all grid points if requested
    if args.map and args.grid:
        try:
            # Generate grid map with all points
            grid_map_output = "grid_" + args.map_output
            MapGenerator.generate_grid_map(
                coordinates=coordinates,
                center_lat=args.lat,
                center_lon=args.lon,
                grid_size=args.grid_size,
                zoom=args.map_zoom,
                output_file=grid_map_output
            )
            
        except Exception as e:
            print(f"\nError generating grid map: {str(e)}")
            print("Make sure you have folium installed (pip install folium)")
            print("To install folium, run: pip install folium")

if __name__ == "__main__":
    main()