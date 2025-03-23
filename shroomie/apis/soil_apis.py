#!/usr/bin/env python3
import requests
import os
from typing import Dict, Any, List, Optional, Union, Tuple

class SoilAPI:
    """Base class for soil-related API calls."""
    
    @staticmethod
    def get_soil_type(lat: float, lon: float, top_k: Optional[int] = None) -> Dict[str, Any]:
        """Get soil type data from OpenEPI API."""
        base_url = "https://api.openepi.io/soil/type"
        
        params = {
            "lat": lat,
            "lon": lon
        }
        
        if top_k is not None:
            params["top_k"] = top_k
        
        response = requests.get(base_url, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API request failed with status code {response.status_code}", "details": response.text}

    @staticmethod
    def get_soil_properties(lat: float, lon: float, depths: Optional[List[str]] = None, 
                           properties: Optional[List[str]] = None, 
                           values: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get soil property data from OpenEPI API.
        
        Args:
            lat (float): Latitude of the location
            lon (float): Longitude of the location
            depths (list): Optional list of depths to query (e.g. ['0-5cm', '5-15cm'])
            properties (list): Optional list of soil properties to query (e.g. ['bdod', 'phh2o'])
            values (list): Optional list of statistical values to return (e.g. ['mean', 'Q0.05'])
            
        Returns:
            dict: Soil property data in GeoJSON format
            
        Example:
            >>> get_soil_properties(45.1451, -123.7521, depths=['0-5cm'], properties=['bdod', 'phh2o'], values=['mean', 'Q0.05'])
        """
        base_url = "https://api.openepi.io/soil/property"
        
        # Build parameters dict
        params = {
            "lat": lat,
            "lon": lon
        }
        
        # Add optional parameters as repeated query parameters
        if depths:
            params["depths"] = depths if isinstance(depths, list) else [depths]
        if properties:
            params["properties"] = properties if isinstance(properties, list) else [properties]
        if values:
            params["values"] = values if isinstance(values, list) else [values]
        
        response = requests.get(base_url, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API request failed with status code {response.status_code}", "details": response.text}

    @staticmethod
    def get_soilgrids_data(lat: float, lon: float, number_classes: int = 5) -> Dict[str, Any]:
        """Get soil data from ISRIC SoilGrids API."""
        base_url = "https://rest.isric.org/soilgrids/v2.0/classification/query"
        
        params = {
            "lat": lat,
            "lon": lon,
            "number_classes": number_classes
        }
        
        response = requests.get(base_url, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"SoilGrids API request failed with status code {response.status_code}", "details": response.text}


class MapboxAPI:
    """Handles interactions with Mapbox API for terrain data."""
    
    @staticmethod
    def get_mapbox_terrain(lat: float, lon: float, mapbox_token: Optional[str] = None) -> Dict[str, Any]:
        """Get terrain data from Mapbox Terrain API.
        Requires access token from https://www.mapbox.com/"""
        
        if not mapbox_token:
            mapbox_token = os.environ.get("MAPBOX_TOKEN")
        
        if not mapbox_token:
            return {"error": "No access token provided for Mapbox. Set MAPBOX_TOKEN environment variable or pass with --mapbox-token"}
        
        base_url = f"https://api.mapbox.com/v4/mapbox.mapbox-terrain-v2/tilequery/{lon},{lat}.json"
        
        params = {
            "access_token": mapbox_token,
            "layers": "contour"
        }
        
        try:
            response = requests.get(base_url, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Mapbox Terrain API request failed with status code {response.status_code}", "details": response.text}
        except Exception as e:
            return {"error": f"Failed to fetch Mapbox terrain data: {str(e)}"}