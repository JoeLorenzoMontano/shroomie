#!/usr/bin/env python3
import datetime
from typing import Dict, Any, Optional, List, Union

class PromptGenerator:
    """Generates LLM prompts based on environmental data."""
    
    @staticmethod
    def generate_llm_prompt(
        openepi_data: Optional[Dict[str, Any]] = None, 
        soilgrids_data: Optional[Dict[str, Any]] = None, 
        elevation_data: Optional[Dict[str, Any]] = None, 
        forest_data: Optional[Dict[str, Any]] = None, 
        topo_data: Optional[Dict[str, Any]] = None, 
        weather_data: Optional[Dict[str, Any]] = None, 
        tree_data: Optional[Dict[str, Any]] = None, 
        soil_properties_data: Optional[Dict[str, Any]] = None, 
        mushroom_type: Optional[str] = None, 
        location_name: Optional[str] = None, 
        location_data: Optional[Dict[str, Any]] = None, 
        lat: Optional[float] = None, 
        lon: Optional[float] = None
    ) -> str:
        """Generate a prompt for LLMs based on soil data and mushroom type."""
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Start with basic prompt structure
        prompt = f"Date: {current_date}\n\n"
        
        # Add location information if available
        if lat is not None and lon is not None:
            prompt += f"Location Coordinates: Latitude {lat}, Longitude {lon}\n"
        
        # Add OpenStreetMap location data if available
        if location_data and "error" not in location_data:
            try:
                if "display_name" in location_data:
                    prompt += f"Location: {location_data['display_name']}\n"
            except (KeyError, TypeError):
                pass
        elif location_name:
            prompt += f"Location Name: {location_name}\n"
        
        # Add mushroom type if specified
        if mushroom_type:
            prompt += f"Target Mushroom: {mushroom_type}\n"
        
        # Add elevation data if available
        prompt += "\nTerrain Information:\n"
        elevation_added = False
        
        if topo_data and "error" not in topo_data:
            try:
                if "elevation" in topo_data:
                    prompt += f"- Elevation (Open-Meteo): {topo_data['elevation']} meters\n"
                    elevation_added = True
            except (KeyError, TypeError):
                pass
        
        if not elevation_added and elevation_data and "error" not in elevation_data:
            try:
                if "elevation" in elevation_data:
                    prompt += f"- Elevation (Open-Elevation): {elevation_data['elevation']} meters\n"
                    elevation_added = True
            except (KeyError, TypeError):
                pass
        
        # Add forest cover data if available
        forest_added = False
        if forest_data and "error" not in forest_data:
            try:
                # For GFW API data
                if "data" in forest_data and "attributes" in forest_data["data"]:
                    attrs = forest_data["data"]["attributes"]
                    if "treeCover" in attrs:
                        prompt += f"- Tree Cover: {attrs['treeCover']}%\n"
                        forest_added = True
                # For estimated data
                elif "estimated_tree_cover" in forest_data:
                    prompt += f"- Tree Cover: {forest_data['estimated_tree_cover']}%\n"
                    if "status" in forest_data:
                        prompt += f"  (Note: {forest_data['status']})\n"
                    
                    # Add dominant tree species if available
                    if "estimated_tree_species" in forest_data and forest_data["estimated_tree_species"]:
                        prompt += "- Dominant Tree Species (estimated):\n"
                        for species in forest_data["estimated_tree_species"]:
                            prompt += f"  * {species}\n"
                    
                    forest_added = True
            except (KeyError, TypeError) as e:
                prompt += f"- Tree Cover: Error processing data - {str(e)}\n"
        
        if not forest_added:
            prompt += "- Tree Cover: Data not available\n"
        
        # Add tree species data if available
        if tree_data and "error" not in tree_data:
            try:
                # Add ecoregion information
                if "ecoregion" in tree_data:
                    prompt += f"- Ecoregion: {tree_data['ecoregion']}\n"
                
                if "forest_type" in tree_data:
                    prompt += f"- Forest Type: {tree_data['forest_type']}\n"
                
                # Add dominant species information
                if "dominant_species" in tree_data and tree_data["dominant_species"]:
                    prompt += "- Dominant Tree Species:\n"
                    for species in tree_data["dominant_species"]:
                        prompt += f"  * {species}\n"
                
                # Add common species information
                if "common_species" in tree_data and tree_data["common_species"]:
                    prompt += "- Common Tree Species:\n"
                    for species in tree_data["common_species"]:
                        prompt += f"  * {species}\n"
                
                # Add understory information
                if "understory" in tree_data and tree_data["understory"]:
                    prompt += "- Understory Vegetation:\n"
                    for species in tree_data["understory"]:
                        prompt += f"  * {species}\n"
                
                # Add mushroom associations if present
                if "mushroom_associations" in tree_data and tree_data["mushroom_associations"]:
                    prompt += "\nMushroom-Tree Associations:\n"
                    for tree, mushrooms in tree_data["mushroom_associations"].items():
                        prompt += f"- {tree}: {', '.join(mushrooms)}\n"
                
            except (KeyError, TypeError):
                pass
        
        # Add land use information if available from OpenStreetMap
        if location_data and "error" not in location_data:
            try:
                if "address" in location_data:
                    address = location_data["address"]
                    if "landuse" in address:
                        prompt += f"- Land Use: {address['landuse']}\n"
                    elif "leisure" in address:
                        prompt += f"- Land Use: {address['leisure']}\n"
                    elif "natural" in address:
                        prompt += f"- Land Type: {address['natural']}\n"
            except (KeyError, TypeError):
                pass
        
        # Add weather data if available
        if weather_data and "error" not in weather_data:
            prompt += "\nRecent Weather Data:\n"
            
            try:
                if "daily" in weather_data:
                    daily = weather_data["daily"]
                    
                    # Process temperature data
                    if "temperature_2m_mean" in daily and daily["temperature_2m_mean"]:
                        # Calculate overall min, max and mean values
                        valid_temps = [t for t in daily["temperature_2m_mean"] if t is not None]
                        if valid_temps:
                            avg_temp = sum(valid_temps) / len(valid_temps)
                            prompt += f"- Average Temperature: {avg_temp:.1f}°C\n"
                        
                        # Minimum temperature
                        if "temperature_2m_min" in daily and daily["temperature_2m_min"]:
                            valid_min_temps = [t for t in daily["temperature_2m_min"] if t is not None]
                            if valid_min_temps:
                                min_temp = min(valid_min_temps)
                                prompt += f"- Minimum Temperature: {min_temp:.1f}°C\n"
                        
                        # Maximum temperature
                        if "temperature_2m_max" in daily and daily["temperature_2m_max"]:
                            valid_max_temps = [t for t in daily["temperature_2m_max"] if t is not None]
                            if valid_max_temps:
                                max_temp = max(valid_max_temps)
                                prompt += f"- Maximum Temperature: {max_temp:.1f}°C\n"
                    
                    # Process precipitation data
                    if "precipitation_sum" in daily and daily["precipitation_sum"]:
                        valid_precip = [p for p in daily["precipitation_sum"] if p is not None]
                        if valid_precip:
                            total_precip = sum(valid_precip)
                            avg_daily_precip = total_precip / len(valid_precip)
                            prompt += f"- Total Precipitation: {total_precip:.1f} mm\n"
                            prompt += f"- Average Daily Precipitation: {avg_daily_precip:.1f} mm\n"
                    
                    # Process rain data
                    if "rain_sum" in daily and daily["rain_sum"]:
                        valid_rain = [r for r in daily["rain_sum"] if r is not None]
                        if valid_rain:
                            total_rain = sum(valid_rain)
                            rainy_days = sum(1 for r in valid_rain if r > 0.1)
                            prompt += f"- Total Rainfall: {total_rain:.1f} mm over {rainy_days} days\n"
                    
                    # Process snow data
                    if "snowfall_sum" in daily and daily["snowfall_sum"]:
                        valid_snow = [s for s in daily["snowfall_sum"] if s is not None]
                        if valid_snow:
                            total_snow = sum(valid_snow)
                            snowy_days = sum(1 for s in valid_snow if s > 0.1)
                            if total_snow > 0:
                                prompt += f"- Total Snowfall: {total_snow:.1f} cm over {snowy_days} days\n"
                else:
                    prompt += "- Weather data is available but in an unexpected format\n"
            except (KeyError, TypeError):
                prompt += "- Weather data available but could not be properly processed\n"
        
        prompt += "\nSoil Information:\n"
        
        # Add OpenEPI soil data if available
        if openepi_data and "error" not in openepi_data:
            try:
                soil_type = openepi_data["properties"]["most_probable_soil_type"]
                prompt += f"- Primary Soil Type (OpenEPI): {soil_type}\n"
                
                # Add probability data if available
                if "probabilities" in openepi_data["properties"]:
                    prompt += "- Soil Type Probabilities (OpenEPI):\n"
                    for soil in openepi_data["properties"]["probabilities"]:
                        prompt += f"  * {soil['soil_type']}: {soil['probability']}%\n"
            except KeyError:
                prompt += "- OpenEPI data available but in unexpected format\n"
        
        # Add SoilGrids data if available
        if soilgrids_data and "error" not in soilgrids_data:
            try:
                wrb_class = soilgrids_data.get("wrb_class_name")
                if wrb_class:
                    prompt += f"- Primary Soil Type (SoilGrids): {wrb_class}\n"
                
                # Add probability data
                if "wrb_class_probability" in soilgrids_data:
                    prompt += "- Soil Type Probabilities (SoilGrids):\n"
                    for soil_data in soilgrids_data["wrb_class_probability"]:
                        prompt += f"  * {soil_data[0]}: {soil_data[1]}%\n"
            except KeyError:
                prompt += "- SoilGrids data available but in unexpected format\n"
        
        # Add Soil Properties data if available
        if soil_properties_data and "error" not in soil_properties_data:
            try:
                prompt += "- Soil Properties:\n"
                
                if "properties" in soil_properties_data and "layers" in soil_properties_data["properties"]:
                    layers = soil_properties_data["properties"]["layers"]
                    
                    for layer in layers:
                        property_name = layer.get("name", layer.get("code", "Unknown"))
                        unit = layer.get("unit_measure", {}).get("target_units", "")
                        
                        prompt += f"  * {property_name}"
                        if unit:
                            prompt += f" ({unit})"
                        prompt += ":\n"
                        
                        # Add depth-specific data
                        if "depths" in layer:
                            for depth in layer["depths"]:
                                depth_label = depth.get("label", "Unknown depth")
                                prompt += f"    - {depth_label}: "
                                
                                if "values" in depth:
                                    values_str = []
                                    for stat, value in depth["values"].items():
                                        # Apply conversion factor if available
                                        conversion = layer.get("unit_measure", {}).get("conversion_factor", 1)
                                        if conversion != 1:
                                            converted_value = value / conversion
                                            values_str.append(f"{stat}={converted_value:.1f}")
                                        else:
                                            values_str.append(f"{stat}={value}")
                                    
                                    prompt += ", ".join(values_str)
                                prompt += "\n"
            except Exception as e:
                prompt += f"  * Error processing soil properties data: {str(e)}\n"
        
        # Add RAG instruction
        if mushroom_type:
            prompt += f"\nBased on the soil, terrain, and weather information above, please evaluate the suitability of this location for growing {mushroom_type} mushrooms. Consider the soil types, elevation, tree cover, temperature, precipitation, and soil moisture patterns, and how these factors might affect mushroom growth. Provide specific recommendations for cultivation techniques that would be appropriate for these environmental conditions."
        else:
            prompt += "\nBased on the soil, terrain, and weather information above, please provide an analysis of what mushroom species might grow well in this environment. Consider soil types, elevation, tree cover, temperature, precipitation patterns, and explain why certain mushrooms would thrive in these conditions."
        
        return prompt