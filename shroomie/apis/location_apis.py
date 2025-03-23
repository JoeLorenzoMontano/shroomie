#!/usr/bin/env python3
import requests
import os
from typing import Dict, Any, Optional, Union

class LocationAPI:
    """Handles location-based API calls."""
    
    @staticmethod
    def get_location_name(lat: float, lon: float) -> Dict[str, Any]:
        """Get location name from OpenStreetMap Nominatim API."""
        base_url = "https://nominatim.openstreetmap.org/reverse"
        
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json"
        }
        
        # Get user agent info from environment variables or use defaults
        app_name = os.environ.get("OSM_USER_AGENT", "ShroomieApp/1.0")
        contact_url = os.environ.get("OSM_CONTACT_URL", "https://github.com/your-username/shroomie")
        contact_email = os.environ.get("OSM_CONTACT_EMAIL", "contact@example.com")
        
        headers = {
            "User-Agent": f"{app_name} ({contact_url}; {contact_email})"
        }
        
        try:
            response = requests.get(base_url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "display_name" in data:
                    return data
                else:
                    return {"error": "No location name found"}
            else:
                return {"error": f"Nominatim API request failed with status code {response.status_code}"}
        except Exception as e:
            return {"error": f"Failed to fetch location data: {str(e)}"}

    @staticmethod
    def geocode_location(location_name: str) -> Dict[str, Any]:
        """Convert location name to coordinates using OpenStreetMap Nominatim API."""
        base_url = "https://nominatim.openstreetmap.org/search"
        
        params = {
            "q": location_name,
            "format": "json"
        }
        
        # Get user agent info from environment variables or use defaults
        app_name = os.environ.get("OSM_USER_AGENT", "ShroomieApp/1.0")
        contact_url = os.environ.get("OSM_CONTACT_URL", "https://github.com/your-username/shroomie")
        contact_email = os.environ.get("OSM_CONTACT_EMAIL", "contact@example.com")
        
        headers = {
            "User-Agent": f"{app_name} ({contact_url}; {contact_email})"
        }
        
        try:
            response = requests.get(base_url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]
                else:
                    return {"error": "No coordinates found for this location"}
            else:
                return {"error": f"Nominatim API request failed with status code {response.status_code}"}
        except Exception as e:
            return {"error": f"Failed to fetch coordinates: {str(e)}"}


class ElevationAPI:
    """Handles elevation data API calls."""
    
    @staticmethod
    def get_elevation_data(lat: float, lon: float) -> Dict[str, Any]:
        """Get elevation data from Open-Elevation API."""
        base_url = "https://api.open-elevation.com/api/v1/lookup"
        
        params = {
            "locations": f"{lat},{lon}"
        }
        
        try:
            response = requests.get(base_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if "results" in data and len(data["results"]) > 0:
                    return data["results"][0]
                else:
                    return {"error": "No elevation data found"}
            else:
                return {"error": f"Elevation API request failed with status code {response.status_code}"}
        except Exception as e:
            return {"error": f"Failed to fetch elevation data: {str(e)}"}

    @staticmethod
    def get_open_topo_data(lat: float, lon: float) -> Dict[str, Any]:
        """Get elevation and other topographic data from Open-Meteo API."""
        base_url = "https://api.open-meteo.com/v1/elevation"
        
        params = {
            "latitude": lat,
            "longitude": lon
        }
        
        try:
            response = requests.get(base_url, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Open-Meteo API request failed with status code {response.status_code}"}
        except Exception as e:
            return {"error": f"Failed to fetch Open-Meteo data: {str(e)}"}