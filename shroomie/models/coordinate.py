#!/usr/bin/env python3
from typing import Tuple, Optional

class Coordinate:
    """Class for handling geographic coordinates and conversions."""
    
    def __init__(self, lat: float, lon: float):
        """Initialize with latitude and longitude in decimal degrees."""
        self.lat = lat
        self.lon = lon
    
    @classmethod
    def from_dms(cls, lat_dms: str, lon_dms: str) -> 'Coordinate':
        """
        Create a Coordinate from degrees-minutes-seconds strings.
        
        Args:
            lat_dms (str): Latitude in DMS format (e.g., "45°05'55.9\"N")
            lon_dms (str): Longitude in DMS format (e.g., "123°47'09.5\"W")
            
        Returns:
            Coordinate: A new Coordinate object
        """
        lat_decimal = cls._dms_to_decimal(lat_dms)
        lon_decimal = cls._dms_to_decimal(lon_dms)
        return cls(lat_decimal, lon_decimal)
    
    @staticmethod
    def _dms_to_decimal(dms: str) -> float:
        """
        Convert a coordinate string in DMS format to decimal degrees.
        
        Args:
            dms (str): Coordinate in DMS format (e.g., "45°05'55.9\"N" or "123°47'09.5\"W")
            
        Returns:
            float: Coordinate in decimal degrees
        """
        # Get the direction (last character)
        direction = dms[-1]
        
        # Extract degrees, minutes, seconds
        parts = dms[:-1].replace('"', '').split('°')
        degrees = float(parts[0])
        
        minutes_parts = parts[1].split("'")
        minutes = float(minutes_parts[0])
        
        if len(minutes_parts) > 1:
            seconds = float(minutes_parts[1])
        else:
            seconds = 0
            
        # Convert to decimal degrees
        decimal = degrees + minutes/60 + seconds/3600
        
        # Apply negative value for South or West
        if direction in ['S', 'W']:
            decimal = -decimal
            
        return decimal
    
    def to_dms(self) -> Tuple[str, str]:
        """
        Convert decimal coordinates to DMS format.
        
        Returns:
            tuple: (latitude_dms, longitude_dms)
        """
        lat_direction = 'N' if self.lat >= 0 else 'S'
        lon_direction = 'E' if self.lon >= 0 else 'W'
        
        lat_abs = abs(self.lat)
        lon_abs = abs(self.lon)
        
        lat_degrees = int(lat_abs)
        lat_minutes = int((lat_abs - lat_degrees) * 60)
        lat_seconds = ((lat_abs - lat_degrees) * 60 - lat_minutes) * 60
        
        lon_degrees = int(lon_abs)
        lon_minutes = int((lon_abs - lon_degrees) * 60)
        lon_seconds = ((lon_abs - lon_degrees) * 60 - lon_minutes) * 60
        
        lat_dms = f"{lat_degrees}°{lat_minutes}'{lat_seconds:.1f}\"{lat_direction}"
        lon_dms = f"{lon_degrees}°{lon_minutes}'{lon_seconds:.1f}\"{lon_direction}"
        
        return lat_dms, lon_dms
    
    def __str__(self) -> str:
        """String representation of the coordinate."""
        return f"({self.lat}, {self.lon})"
    
    def __repr__(self) -> str:
        """Official string representation of the coordinate."""
        return f"Coordinate(lat={self.lat}, lon={self.lon})"