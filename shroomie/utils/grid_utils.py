#!/usr/bin/env python3
import math
from typing import List, Tuple

class GridUtils:
    """Utilities for grid-based coordinate calculations."""
    
    @staticmethod
    def calculate_grid_coordinates(center_lat: float, center_lon: float, grid_size: int = 3, distance_miles: float = 1.0) -> List[Tuple[float, float]]:
        """
        Calculate coordinates for a grid around a center point.
        
        Args:
            center_lat (float): Latitude of the center point
            center_lon (float): Longitude of the center point
            grid_size (int): Size of the grid (e.g., 3 for a 3x3 grid)
            distance_miles (float): Distance between points in miles
            
        Returns:
            list: List of (lat, lon) coordinate tuples for the grid
        """
        # Convert miles to approximate degrees
        # These are rough approximations that work for most latitudes
        # 1 degree of latitude is approximately 69 miles
        # 1 degree of longitude varies with latitude, roughly cos(lat) * 69 miles
        lat_offset = distance_miles / 69.0
        lon_offset = distance_miles / (69.0 * abs(math.cos(math.radians(center_lat))))
        
        # Calculate the starting point (top-left corner of the grid)
        half_size = (grid_size - 1) / 2
        start_lat = center_lat + (half_size * lat_offset)
        start_lon = center_lon - (half_size * lon_offset)
        
        # Generate the grid coordinates
        coordinates = []
        for i in range(grid_size):
            for j in range(grid_size):
                lat = start_lat - (i * lat_offset)
                lon = start_lon + (j * lon_offset)
                coordinates.append((lat, lon))
        
        return coordinates