#!/usr/bin/env python3
from typing import Dict, Any, List, Optional, Union, Tuple

class MapGenerator:
    """Generates interactive maps for visualization."""
    
    @staticmethod
    def generate_map(lat: float, lon: float, zoom: int = 10, output_file: str = "location_map.html", 
                    include_soil_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Generate an interactive map showing the location coordinates.
        
        Args:
            lat (float): Latitude of the location
            lon (float): Longitude of the location
            zoom (int): Initial zoom level for the map (default: 10)
            output_file (str): Filename to save the map as HTML (default: "location_map.html")
            include_soil_data (dict): Optional soil data to include in the popup
            
        Returns:
            str: Path to the generated HTML file
        """
        try:
            import folium
        except ImportError:
            print("Error: folium package is not installed. Install it with: pip install folium")
            return None
        
        # Create a map centered at the coordinates
        my_map = folium.Map(location=[lat, lon], zoom_start=zoom)
        
        # Prepare popup content
        popup_content = f"Coordinates: {lat}, {lon}"
        
        # Add soil data to popup if available
        if include_soil_data and "error" not in include_soil_data:
            popup_content += "<br><b>Soil Properties:</b><br>"
            
            try:
                if "properties" in include_soil_data and "layers" in include_soil_data["properties"]:
                    layers = include_soil_data["properties"]["layers"]
                    
                    for layer in layers:
                        property_name = layer.get("name", layer.get("code", "Unknown"))
                        unit = layer.get("unit_measure", {}).get("target_units", "")
                        conversion = layer.get("unit_measure", {}).get("conversion_factor", 1)
                        
                        popup_content += f"<br><b>{property_name}</b>"
                        if unit:
                            popup_content += f" ({unit})"
                        popup_content += ":<br>"
                        
                        if "depths" in layer:
                            for depth in layer["depths"]:
                                depth_label = depth.get("label", "Unknown depth")
                                popup_content += f"&nbsp;&nbsp;{depth_label}: "
                                
                                if "values" in depth:
                                    values_str = []
                                    for stat, value in depth["values"].items():
                                        # Apply conversion factor if available
                                        if conversion != 1:
                                            converted_value = value / conversion
                                            values_str.append(f"{stat}={converted_value:.1f}")
                                        else:
                                            values_str.append(f"{stat}={value}")
                                    
                                    popup_content += ", ".join(values_str)
                                popup_content += "<br>"
            except Exception as e:
                popup_content += f"<br>Error processing soil data: {str(e)}<br>"
        
        # Add a marker at the coordinates with the popup
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip="Click for soil data"
        ).add_to(my_map)
        
        # Save the map as an HTML file
        my_map.save(output_file)
        print(f"Map saved to {output_file}")
        
        return output_file
    
    @staticmethod
    def generate_grid_map(coordinates: List[Tuple[float, float]], center_lat: float, center_lon: float, 
                          grid_size: int, zoom: int = 10, output_file: str = "grid_map.html") -> Optional[str]:
        """
        Generate an interactive map showing a grid of points.
        
        Args:
            coordinates (list): List of (lat, lon) tuples for all grid points
            center_lat (float): Latitude of the center point
            center_lon (float): Longitude of the center point
            grid_size (int): Size of the grid (e.g., 3 for a 3x3 grid)
            zoom (int): Initial zoom level for the map (default: 10)
            output_file (str): Filename to save the map as HTML (default: "grid_map.html")
            
        Returns:
            str: Path to the generated HTML file
        """
        try:
            import folium
        except ImportError:
            print("Error: folium package is not installed. Install it with: pip install folium")
            return None
        
        # Create a map centered at the original coordinates
        my_map = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)
        
        # Organize grid points and find boundaries
        grid_points = {}
        min_lat = float('inf')
        max_lat = float('-inf')
        min_lon = float('inf')
        max_lon = float('-inf')
        
        # Group coordinates into a 2D grid structure for easier line drawing
        point_idx = 0
        for i in range(grid_size):
            for j in range(grid_size):
                lat, lon = coordinates[point_idx]
                if (i, j) not in grid_points:
                    grid_points[(i, j)] = (lat, lon)
                
                # Track boundaries
                min_lat = min(min_lat, lat)
                max_lat = max(max_lat, lat)
                min_lon = min(min_lon, lon)
                max_lon = max(max_lon, lon)
                
                point_idx += 1
        
        # Add grid lines
        # Horizontal lines
        for i in range(grid_size):
            points = []
            for j in range(grid_size):
                lat, lon = grid_points[(i, j)]
                points.append([lat, lon])
            
            # Create a polyline for this row
            folium.PolyLine(
                locations=points,
                color="blue",
                weight=2,
                opacity=0.7,
                dash_array="5, 5"
            ).add_to(my_map)
        
        # Vertical lines
        for j in range(grid_size):
            points = []
            for i in range(grid_size):
                lat, lon = grid_points[(i, j)]
                points.append([lat, lon])
            
            # Create a polyline for this column
            folium.PolyLine(
                locations=points,
                color="blue",
                weight=2,
                opacity=0.7,
                dash_array="5, 5"
            ).add_to(my_map)
        
        # Add outline around the entire grid
        boundary_points = [
            [min_lat, min_lon],
            [min_lat, max_lon],
            [max_lat, max_lon],
            [max_lat, min_lon],
            [min_lat, min_lon]
        ]
        folium.PolyLine(
            locations=boundary_points,
            color="red",
            weight=3,
            opacity=0.9
        ).add_to(my_map)
        
        # Add markers for all grid points
        for idx, (lat, lon) in enumerate(coordinates):
            popup_content = f"Point {idx+1}: {lat}, {lon}"
            
            # Make the center point a different color
            if idx == len(coordinates) // 2:  # Center point in the grid
                folium.Marker(
                    location=[lat, lon],
                    popup=popup_content,
                    tooltip="Center point",
                    icon=folium.Icon(color="red")
                ).add_to(my_map)
            else:
                folium.Marker(
                    location=[lat, lon],
                    popup=popup_content,
                    tooltip=f"Point {idx+1}"
                ).add_to(my_map)
        
        # Save the map
        my_map.save(output_file)
        print(f"\nGrid map has been generated at: {output_file}")
        print(f"Open the file in a web browser to view the interactive map.")
        
        return output_file