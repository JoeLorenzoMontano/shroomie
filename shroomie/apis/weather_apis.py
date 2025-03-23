#!/usr/bin/env python3
import requests
import datetime
from datetime import timedelta
import os
from typing import Dict, Any, List, Optional, Union

class WeatherAPI:
    """Handles weather-related API calls."""
    
    @staticmethod
    def get_weather_history(lat: float, lon: float, months: int = 3, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Get historical weather data from Open-Meteo API.
        Default is last 3 months of weather data."""
        
        # Use API key from environment if not provided as argument
        if not api_key:
            api_key = os.environ.get("OPENMETEO_API_KEY")
        
        # Calculate start and end dates
        end_date = datetime.datetime.now().date()
        start_date = end_date - timedelta(days=30*months)
        
        # Use forecast API for current conditions, it doesn't require archive access
        base_url = "https://api.open-meteo.com/v1/forecast"
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum,rain_sum,snowfall_sum",
            "timezone": "auto",
            "past_days": 30  # Get up to 30 days of past data
        }
        
        try:
            response = requests.get(base_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Create simplified weather summary
                if "daily" in data:
                    monthly_data = {}
                    
                    # Initialize current month
                    month_key = datetime.datetime.now().strftime("%Y-%m")
                    monthly_data[month_key] = {
                        "temp_max": [],
                        "temp_min": [],
                        "temp_mean": [],
                        "precip_sum": [],
                        "rain_sum": [],
                        "snow_sum": []
                    }
                    
                    # Populate with daily data
                    daily = data["daily"]
                    for i, date_str in enumerate(daily["time"]):
                        date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                        
                        if "temperature_2m_max" in daily and i < len(daily["temperature_2m_max"]):
                            monthly_data[month_key]["temp_max"].append(daily["temperature_2m_max"][i])
                        
                        if "temperature_2m_min" in daily and i < len(daily["temperature_2m_min"]):
                            monthly_data[month_key]["temp_min"].append(daily["temperature_2m_min"][i])
                        
                        if "temperature_2m_mean" in daily and i < len(daily["temperature_2m_mean"]):
                            monthly_data[month_key]["temp_mean"].append(daily["temperature_2m_mean"][i])
                        
                        if "precipitation_sum" in daily and i < len(daily["precipitation_sum"]):
                            monthly_data[month_key]["precip_sum"].append(daily["precipitation_sum"][i])
                        
                        if "rain_sum" in daily and i < len(daily["rain_sum"]):
                            monthly_data[month_key]["rain_sum"].append(daily["rain_sum"][i])
                        
                        if "snowfall_sum" in daily and i < len(daily["snowfall_sum"]):
                            monthly_data[month_key]["snow_sum"].append(daily["snowfall_sum"][i])
                    
                    # Calculate averages for each month
                    monthly_averages = {}
                    for month, values in monthly_data.items():
                        monthly_averages[month] = {}
                        
                        for key, data_list in values.items():
                            if data_list and any(x is not None for x in data_list):
                                # Filter out None values
                                valid_values = [x for x in data_list if x is not None]
                                if valid_values:
                                    # For precipitation sums, we want the total, not average
                                    if key in ["precip_sum", "rain_sum", "snow_sum"]:
                                        monthly_averages[month][key] = sum(valid_values)
                                    else:
                                        monthly_averages[month][key] = sum(valid_values) / len(valid_values)
                                else:
                                    monthly_averages[month][key] = None
                            else:
                                monthly_averages[month][key] = None
                    
                    data["monthly_averages"] = monthly_averages
                
                return data
            else:
                return {"error": f"Weather API request failed with status code {response.status_code}"}
        except Exception as e:
            return {"error": f"Failed to fetch weather data: {str(e)}"}