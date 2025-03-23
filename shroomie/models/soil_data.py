#!/usr/bin/env python3
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

@dataclass
class SoilType:
    """Class representing a soil type with probability."""
    name: str
    probability: float
    
    def __str__(self) -> str:
        return f"{self.name}: {self.probability}%"

@dataclass
class SoilPropertyValue:
    """Class representing a soil property value at a specific depth."""
    depth: str  # e.g., "0-5cm"
    property_name: str  # e.g., "pH", "clay content"
    values: Dict[str, float]  # e.g., {"mean": 6.2, "Q0.05": 5.8}
    unit: str = ""
    
    def __str__(self) -> str:
        values_str = ", ".join([f"{k}={v}" for k, v in self.values.items()])
        if self.unit:
            return f"{self.property_name} at {self.depth} ({self.unit}): {values_str}"
        else:
            return f"{self.property_name} at {self.depth}: {values_str}"

class SoilData:
    """Class for organizing and processing soil data from various APIs."""
    
    def __init__(self, 
                lat: float, 
                lon: float, 
                soilgrids_data: Optional[Dict[str, Any]] = None,
                openepi_data: Optional[Dict[str, Any]] = None,
                soil_properties_data: Optional[Dict[str, Any]] = None):
        """Initialize with data from soil APIs."""
        self.lat = lat
        self.lon = lon
        self.soilgrids_data = soilgrids_data
        self.openepi_data = openepi_data
        self.soil_properties_data = soil_properties_data
        
        # Processed data
        self.primary_soil_type: Optional[str] = None
        self.soil_types: List[SoilType] = []
        self.soil_properties: List[SoilPropertyValue] = []
        
        # Process the data if available
        self._process_data()
    
    def _process_data(self) -> None:
        """Process the raw API data into structured properties."""
        # Process SoilGrids data
        if self.soilgrids_data and "error" not in self.soilgrids_data:
            try:
                # Get primary soil type
                self.primary_soil_type = self.soilgrids_data.get("wrb_class_name")
                
                # Get soil type probabilities
                if "wrb_class_probability" in self.soilgrids_data:
                    for soil_data in self.soilgrids_data["wrb_class_probability"]:
                        soil_type = SoilType(
                            name=soil_data[0],
                            probability=soil_data[1]
                        )
                        self.soil_types.append(soil_type)
            except (KeyError, TypeError):
                pass
        
        # Process OpenEPI data
        if self.openepi_data and "error" not in self.openepi_data:
            try:
                if not self.primary_soil_type and "properties" in self.openepi_data:
                    self.primary_soil_type = self.openepi_data["properties"].get("most_probable_soil_type")
                
                # Add soil type probabilities if available
                if "properties" in self.openepi_data and "probabilities" in self.openepi_data["properties"]:
                    for soil in self.openepi_data["properties"]["probabilities"]:
                        soil_type = SoilType(
                            name=soil['soil_type'],
                            probability=soil['probability']
                        )
                        self.soil_types.append(soil_type)
            except (KeyError, TypeError):
                pass
        
        # Process soil properties data
        if self.soil_properties_data and "error" not in self.soil_properties_data:
            try:
                if "properties" in self.soil_properties_data and "layers" in self.soil_properties_data["properties"]:
                    layers = self.soil_properties_data["properties"]["layers"]
                    
                    for layer in layers:
                        property_name = layer.get("name", layer.get("code", "Unknown"))
                        unit = layer.get("unit_measure", {}).get("target_units", "")
                        
                        # Process depths
                        if "depths" in layer:
                            for depth in layer["depths"]:
                                depth_label = depth.get("label", "Unknown depth")
                                
                                if "values" in depth:
                                    # Convert values if needed
                                    conversion = layer.get("unit_measure", {}).get("conversion_factor", 1)
                                    values = {}
                                    
                                    for stat, value in depth["values"].items():
                                        if conversion != 1:
                                            values[stat] = value / conversion
                                        else:
                                            values[stat] = value
                                    
                                    soil_property = SoilPropertyValue(
                                        depth=depth_label,
                                        property_name=property_name,
                                        values=values,
                                        unit=unit
                                    )
                                    self.soil_properties.append(soil_property)
            except (KeyError, TypeError):
                pass
    
    def get_primary_soil_type(self) -> str:
        """Get the primary soil type or 'Unknown' if not available."""
        return self.primary_soil_type or "Unknown"
    
    def get_soil_types_ranked(self) -> List[SoilType]:
        """Get soil types ranked by probability."""
        return sorted(self.soil_types, key=lambda x: x.probability, reverse=True)
    
    def get_property_by_name(self, name: str) -> List[SoilPropertyValue]:
        """Get all soil properties matching a given name."""
        return [prop for prop in self.soil_properties if name.lower() in prop.property_name.lower()]
    
    def get_ph_values(self) -> List[SoilPropertyValue]:
        """Get pH values if available."""
        return self.get_property_by_name("pH") or self.get_property_by_name("phh2o")
    
    def get_clay_content(self) -> List[SoilPropertyValue]:
        """Get clay content values if available."""
        return self.get_property_by_name("clay")
    
    def get_sand_content(self) -> List[SoilPropertyValue]:
        """Get sand content values if available."""
        return self.get_property_by_name("sand")
    
    def get_organic_matter(self) -> List[SoilPropertyValue]:
        """Get organic matter or carbon content values if available."""
        return self.get_property_by_name("organic") or self.get_property_by_name("carbon")
    
    def __str__(self) -> str:
        """String representation of the soil data."""
        result = f"Soil Data for coordinates ({self.lat}, {self.lon}):\n"
        
        if self.primary_soil_type:
            result += f"Primary Soil Type: {self.primary_soil_type}\n"
        
        if self.soil_types:
            result += "Soil Types by Probability:\n"
            for soil_type in self.get_soil_types_ranked():
                result += f"  - {soil_type}\n"
        
        if self.soil_properties:
            result += "Soil Properties:\n"
            for prop in self.soil_properties:
                result += f"  - {prop}\n"
        
        return result