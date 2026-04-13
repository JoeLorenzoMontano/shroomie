"""Heatmap visualization generator for mushroom suitability scores."""

import numpy as np
from typing import List, Tuple, Dict, Any
from scipy.interpolate import griddata


class HeatmapGenerator:
    """Generates heatmap visualizations for suitability scores."""

    @staticmethod
    def generate_heatmap_data(coordinates: List[Tuple[float, float]],
                              scores: List[float],
                              resolution: int = 20) -> List[List[float]]:
        """
        Generate heatmap data from coordinates and scores.

        Args:
            coordinates: List of (lat, lon) tuples
            scores: List of suitability scores (0-100)
            resolution: Grid resolution for interpolation

        Returns:
            List of [lat, lon, intensity] for HeatMap plugin
        """
        if not coordinates or not scores:
            return []

        # Convert to numpy arrays
        coords_array = np.array(coordinates)
        scores_array = np.array(scores)

        # Normalize scores to 0-1 range for heatmap intensity
        normalized_scores = scores_array / 100.0

        # Combine coordinates with normalized scores
        heatmap_data = []
        for (lat, lon), intensity in zip(coordinates, normalized_scores):
            heatmap_data.append([lat, lon, intensity])

        return heatmap_data

    @staticmethod
    def interpolate_grid_scores(grid_scores: Dict[Tuple[float, float], float],
                                resolution: int = 20) -> List[List[float]]:
        """
        Interpolate between grid points for smooth heatmap.

        Uses bilinear interpolation to create a dense grid from sparse data points.

        Args:
            grid_scores: Dict mapping (lat, lon) to suitability score
            resolution: Number of interpolation points between grid points

        Returns:
            List of [lat, lon, intensity] for HeatMap plugin
        """
        if not grid_scores:
            return []

        # Extract coordinates and scores
        points = np.array(list(grid_scores.keys()))
        values = np.array(list(grid_scores.values()))

        # Normalize scores to 0-1 range
        normalized_values = values / 100.0

        # Create interpolation grid
        lat_min, lat_max = points[:, 0].min(), points[:, 0].max()
        lon_min, lon_max = points[:, 1].min(), points[:, 1].max()

        # Create dense grid
        lat_grid = np.linspace(lat_min, lat_max, resolution)
        lon_grid = np.linspace(lon_min, lon_max, resolution)
        grid_lat, grid_lon = np.meshgrid(lat_grid, lon_grid)

        # Interpolate values onto dense grid
        grid_values = griddata(points, normalized_values, (grid_lat, grid_lon), method='cubic')

        # Convert to heatmap data format
        heatmap_data = []
        for i in range(resolution):
            for j in range(resolution):
                lat = grid_lat[i, j]
                lon = grid_lon[i, j]
                intensity = grid_values[i, j]

                # Skip NaN values (outside interpolation range)
                if not np.isnan(intensity):
                    # Clamp intensity to 0-1 range
                    intensity = max(0.0, min(1.0, intensity))
                    heatmap_data.append([lat, lon, intensity])

        return heatmap_data

    @staticmethod
    def create_color_gradient(score: float) -> str:
        """
        Convert score (0-100) to color hex code.

        Gradient: Red (0) → Yellow (50) → Green (100)

        Args:
            score: Suitability score (0-100)

        Returns:
            Hex color code (e.g., '#ff0000')
        """
        # Clamp score to 0-100 range
        score = max(0, min(100, score))

        if score <= 50:
            # Red to Yellow (0-50)
            ratio = score / 50.0
            r = 255
            g = int(255 * ratio)
            b = 0
        else:
            # Yellow to Green (50-100)
            ratio = (score - 50) / 50.0
            r = int(255 * (1 - ratio))
            g = 255
            b = 0

        return f'#{r:02x}{g:02x}{b:02x}'

    @staticmethod
    def get_score_color_class(score: float) -> str:
        """
        Get Bootstrap color class for a score.

        Args:
            score: Suitability score (0-100)

        Returns:
            Bootstrap color class name
        """
        if score >= 90:
            return 'success'  # Green
        elif score >= 75:
            return 'success'  # Green
        elif score >= 60:
            return 'primary'  # Blue
        elif score >= 40:
            return 'warning'  # Yellow/Orange
        else:
            return 'danger'   # Red

    @staticmethod
    def create_marker_icon(score: float, is_center: bool = False):
        """
        Create a folium icon based on suitability score.

        Args:
            score: Suitability score (0-100)
            is_center: Whether this is the center point of a grid

        Returns:
            Folium Icon object
        """
        import folium

        if is_center:
            return folium.Icon(color='red', icon='star', prefix='fa')

        # Color based on score
        if score >= 75:
            color = 'green'
            icon = 'leaf'
        elif score >= 60:
            color = 'blue'
            icon = 'info-sign'
        elif score >= 40:
            color = 'orange'
            icon = 'warning-sign'
        else:
            color = 'red'
            icon = 'remove-sign'

        return folium.Icon(color=color, icon=icon)

    @staticmethod
    def create_circle_marker(lat: float, lon: float, score: float,
                            species_name: str, popup_data: Dict[str, Any] = None):
        """
        Create a colored circle marker for a location.

        Args:
            lat: Latitude
            lon: Longitude
            score: Suitability score (0-100)
            species_name: Name of the species
            popup_data: Optional additional data for popup

        Returns:
            Folium CircleMarker object
        """
        import folium

        color = HeatmapGenerator.create_color_gradient(score)

        # Create popup text
        popup_html = f"""
        <div style="font-family: Arial; min-width: 200px;">
            <h4 style="margin: 0 0 10px 0;">{species_name}</h4>
            <p style="margin: 5px 0;"><strong>Suitability Score:</strong> {score:.1f}/100</p>
            <p style="margin: 5px 0;"><strong>Coordinates:</strong> {lat:.4f}, {lon:.4f}</p>
        """

        if popup_data:
            if popup_data.get('elevation'):
                popup_html += f"<p style='margin: 5px 0;'><strong>Elevation:</strong> {popup_data['elevation']}m</p>"
            if popup_data.get('factors'):
                popup_html += "<p style='margin: 5px 0;'><strong>Top Factors:</strong></p><ul style='margin: 5px 0; padding-left: 20px;'>"
                for factor, factor_score in list(popup_data['factors'].items())[:3]:
                    popup_html += f"<li>{factor}: {factor_score:.0f}</li>"
                popup_html += "</ul>"

        popup_html += "</div>"

        return folium.CircleMarker(
            location=[lat, lon],
            radius=8,
            popup=folium.Popup(popup_html, max_width=300),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=2
        )

    @staticmethod
    def get_heatmap_gradient() -> Dict[float, str]:
        """
        Get the color gradient for folium HeatMap.

        Returns:
            Dict mapping 0-1 values to color codes
        """
        return {
            0.0: 'red',
            0.25: 'orange',
            0.5: 'yellow',
            0.75: 'lightgreen',
            1.0: 'green'
        }
