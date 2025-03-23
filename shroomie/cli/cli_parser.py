#!/usr/bin/env python3
import argparse
from typing import Dict, Any, List, Optional, Union, Tuple

class CliParser:
    """Command-line argument parser for the Shroomie application."""
    
    @staticmethod
    def create_parser() -> argparse.ArgumentParser:
        """Create an ArgumentParser with all options."""
        parser = argparse.ArgumentParser(description="Query environmental APIs and generate LLM prompts")
        
        # Coordinates and location
        location_group = parser.add_argument_group("Location Options")
        location_group.add_argument("--lat", type=float, help="Latitude")
        location_group.add_argument("--lon", type=float, help="Longitude")
        location_group.add_argument("--location", type=str, help="Location name to geocode")
        location_group.add_argument("--osm", action="store_true", help="Query OpenStreetMap for location data")
        location_group.add_argument("--location-name", type=str, help="Name of the location for the prompt")
        
        # Soil APIs
        soil_group = parser.add_argument_group("Soil API Options")
        soil_group.add_argument("--top-k", type=int, help="Return top K soil types with probabilities from OpenEPI")
        soil_group.add_argument("--soilgrids", action="store_true", help="Query SoilGrids API")
        soil_group.add_argument("--openepi", action="store_true", help="Query OpenEPI API for soil type")
        soil_group.add_argument("--soil-properties", action="store_true", help="Query OpenEPI API for soil properties")
        soil_group.add_argument("--depths", type=str, nargs="+", help="Soil depths to query (e.g. 0-5cm 5-15cm)")
        soil_group.add_argument("--properties", type=str, nargs="+", help="Soil properties to query (e.g. bdod phh2o)")
        soil_group.add_argument("--values", type=str, nargs="+", help="Statistical values to return (e.g. mean Q0.05)")
        soil_group.add_argument("--number-classes", type=int, default=5, help="Number of classes to return from SoilGrids")
        
        # Terrain and elevation
        terrain_group = parser.add_argument_group("Terrain and Elevation Options")
        terrain_group.add_argument("--elevation", action="store_true", help="Query elevation data")
        terrain_group.add_argument("--topo", action="store_true", help="Query topographic data from Open-Meteo")
        terrain_group.add_argument("--mapbox-token", type=str, help="Access token for Mapbox")
        
        # Forest and tree data
        forest_group = parser.add_argument_group("Forest and Tree Options")
        forest_group.add_argument("--forest", action="store_true", help="Query forest cover data")
        forest_group.add_argument("--trees", action="store_true", help="Query tree species data")
        forest_group.add_argument("--gfw-api-key", type=str, help="API key for Global Forest Watch")
        
        # Weather data
        weather_group = parser.add_argument_group("Weather Options")
        weather_group.add_argument("--weather", action="store_true", help="Query historical weather data")
        weather_group.add_argument("--months", type=int, default=3, help="Number of months of weather history (default: 3)")
        
        # Global options
        parser.add_argument("--all", action="store_true", help="Query all available APIs")
        
        # Output options
        output_group = parser.add_argument_group("Output Options")
        output_group.add_argument("--prompt", action="store_true", help="Generate LLM prompt")
        output_group.add_argument("--mushroom-type", type=str, help="Target mushroom type for the prompt")
        
        # Map options
        map_group = parser.add_argument_group("Map Options")
        map_group.add_argument("--map", action="store_true", help="Generate interactive map showing location and soil data")
        map_group.add_argument("--map-output", type=str, default="location_map.html", help="Filename for the generated map HTML (default: location_map.html)")
        map_group.add_argument("--map-zoom", type=int, default=10, help="Initial zoom level for the map (default: 10)")
        
        # Grid options
        grid_group = parser.add_argument_group("Grid Analysis Options")
        grid_group.add_argument("--grid", action="store_true", help="Generate a grid of points around the given coordinates")
        grid_group.add_argument("--grid-size", type=int, default=3, help="Size of the grid (e.g., 3 for a 3x3 grid)")
        grid_group.add_argument("--grid-distance", type=float, default=1.0, help="Distance between grid points in miles")
        
        return parser
    
    @staticmethod
    def parse_arguments() -> argparse.Namespace:
        """Parse command-line arguments."""
        parser = CliParser.create_parser()
        args = parser.parse_args()
        return args
    
    @staticmethod
    def validate_arguments(args: argparse.Namespace) -> Tuple[bool, Optional[str]]:
        """
        Validate arguments for logical consistency and required values.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        # Check for valid location input
        if not args.lat or not args.lon:
            if not args.location:
                return False, "Either --lat and --lon or --location must be provided"
        
        return True, None