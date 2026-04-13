"""Suitability scoring engine for mushroom species."""

import math
from typing import Dict, Any, List, Optional
from datetime import datetime


class SuitabilityScorer:
    """Calculates numerical suitability scores (0-100) for mushroom species based on environmental data."""

    def __init__(self, species_data: Dict[str, Any]):
        """
        Initialize scorer with species requirements.

        Args:
            species_data: Species data dict from SpeciesDatabase
        """
        self.species_data = species_data
        self.requirements = species_data.get('requirements', {})
        self.weights = species_data.get('scoring_weights', {})

    def calculate_score(self,
                       environmental_data: Dict[str, Any],
                       custom_weights: Optional[Dict[str, float]] = None,
                       current_month: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculate suitability score based on environmental conditions.

        Args:
            environmental_data: Dict containing environmental data:
                - soil_ph: float
                - dominant_trees: List[str]
                - elevation: float (meters)
                - precipitation: float (mm)
                - temperature_mean: float (Celsius)
                - temperature_min: float
                - temperature_max: float
            custom_weights: Optional custom weighting (overrides species defaults)
            current_month: Month for seasonal scoring (1-12), defaults to current month

        Returns:
            Dict with overall_score, factor_scores, and details
        """
        # Use custom weights if provided, otherwise use species defaults
        weights = custom_weights if custom_weights else self.weights

        # Normalize weights to sum to 1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        # Calculate individual factor scores
        factor_scores = {}
        factor_details = {}

        # Soil pH
        if 'soil_ph' in weights and environmental_data.get('soil_ph') is not None:
            ph_score, ph_detail = self._score_soil_ph(environmental_data['soil_ph'])
            factor_scores['soil_ph'] = ph_score
            factor_details['soil_ph'] = ph_detail

        # Tree associations
        if 'tree_association' in weights and environmental_data.get('dominant_trees'):
            tree_score, tree_detail = self._score_tree_association(environmental_data['dominant_trees'])
            factor_scores['tree_association'] = tree_score
            factor_details['tree_association'] = tree_detail

        # Elevation
        if 'elevation' in weights and environmental_data.get('elevation') is not None:
            elev_score, elev_detail = self._score_elevation(environmental_data['elevation'])
            factor_scores['elevation'] = elev_score
            factor_details['elevation'] = elev_detail

        # Moisture (from precipitation)
        if 'moisture' in weights and environmental_data.get('precipitation') is not None:
            moisture_score, moisture_detail = self._score_moisture(
                environmental_data['precipitation'],
                environmental_data.get('soil_moisture')
            )
            factor_scores['moisture'] = moisture_score
            factor_details['moisture'] = moisture_detail

        # Temperature
        if 'temperature' in weights and environmental_data.get('temperature_mean') is not None:
            temp_score, temp_detail = self._score_temperature(environmental_data)
            factor_scores['temperature'] = temp_score
            factor_details['temperature'] = temp_detail

        # Season
        if 'season' in weights:
            if current_month is None:
                current_month = datetime.now().month
            season_score, season_detail = self._score_season(current_month)
            factor_scores['season'] = season_score
            factor_details['season'] = season_detail

        # Calculate weighted overall score
        overall_score = 0.0
        for factor, score in factor_scores.items():
            if factor in weights:
                overall_score += score * weights[factor]

        return {
            'overall_score': round(overall_score, 2),
            'factor_scores': {k: round(v, 2) for k, v in factor_scores.items()},
            'details': factor_details,
            'weights_used': weights
        }

    def _score_soil_ph(self, ph_value: float) -> tuple:
        """
        Score soil pH using Gaussian curve around optimal.

        Args:
            ph_value: Soil pH value

        Returns:
            Tuple of (score, detail_dict)
        """
        ph_req = self.requirements.get('soil_ph', {})
        optimal = ph_req.get('optimal', 6.5)
        min_ph = ph_req.get('min', 4.5)
        max_ph = ph_req.get('max', 7.5)

        # Check if pH is within acceptable range
        if ph_value < min_ph or ph_value > max_ph:
            score = max(0, 50 - abs(ph_value - optimal) * 20)  # Penalty outside range
        else:
            # Gaussian scoring: 100 at optimal, decreases with distance
            distance = abs(ph_value - optimal)
            sigma = (max_ph - min_ph) / 4  # Standard deviation
            score = 100 * math.exp(-0.5 * (distance / sigma) ** 2)

        detail = {
            'value': ph_value,
            'optimal': optimal,
            'range': f"{min_ph}-{max_ph}",
            'assessment': self._get_assessment(score)
        }

        return score, detail

    def _score_tree_association(self, dominant_trees: List[str]) -> tuple:
        """
        Score based on presence of associated trees.

        Args:
            dominant_trees: List of dominant tree species names

        Returns:
            Tuple of (score, detail_dict)
        """
        tree_req = self.requirements.get('tree_associations', {})
        primary_trees = tree_req.get('primary', [])
        secondary_trees = tree_req.get('secondary', [])

        # Count matches
        primary_matches = [tree for tree in dominant_trees if tree in primary_trees]
        secondary_matches = [tree for tree in dominant_trees if tree in secondary_trees]

        # Scoring: 100 for primary matches, 60 for secondary, weighted by count
        if primary_matches:
            # 100 base score + bonus for multiple primary trees
            score = min(100, 100 + len(primary_matches) * 5)
        elif secondary_matches:
            # 60-80 range for secondary trees
            score = min(80, 60 + len(secondary_matches) * 10)
        else:
            # Penalty for no matches
            score = 30

        detail = {
            'primary_matches': primary_matches,
            'secondary_matches': secondary_matches,
            'primary_required': primary_trees,
            'assessment': self._get_assessment(score)
        }

        return score, detail

    def _score_elevation(self, elevation_m: float) -> tuple:
        """
        Score elevation with optimal range.

        Args:
            elevation_m: Elevation in meters

        Returns:
            Tuple of (score, detail_dict)
        """
        elev_req = self.requirements.get('elevation', {})
        min_elev = elev_req.get('min', 0)
        max_elev = elev_req.get('max', 2000)
        optimal_min = elev_req.get('optimal_min', min_elev)
        optimal_max = elev_req.get('optimal_max', max_elev)

        if optimal_min <= elevation_m <= optimal_max:
            # Within optimal range
            score = 100
        elif min_elev <= elevation_m <= max_elev:
            # Within acceptable range but not optimal
            if elevation_m < optimal_min:
                # Below optimal
                distance = optimal_min - elevation_m
                penalty_range = optimal_min - min_elev
            else:
                # Above optimal
                distance = elevation_m - optimal_max
                penalty_range = max_elev - optimal_max

            if penalty_range > 0:
                score = max(50, 100 - (distance / penalty_range) * 50)
            else:
                score = 75
        else:
            # Outside acceptable range
            if elevation_m < min_elev:
                distance = min_elev - elevation_m
            else:
                distance = elevation_m - max_elev
            score = max(0, 50 - distance / 100)

        detail = {
            'value': elevation_m,
            'optimal_range': f"{optimal_min}-{optimal_max}m",
            'acceptable_range': f"{min_elev}-{max_elev}m",
            'assessment': self._get_assessment(score)
        }

        return score, detail

    def _score_moisture(self, precipitation: float, soil_moisture: Optional[float] = None) -> tuple:
        """
        Score moisture conditions based on precipitation.

        Args:
            precipitation: Precipitation in mm (monthly or recent period)
            soil_moisture: Optional soil moisture percentage

        Returns:
            Tuple of (score, detail_dict)
        """
        moisture_req = self.requirements.get('moisture', {})
        optimal = moisture_req.get('optimal', 65)
        min_moisture = moisture_req.get('min', 40)
        max_moisture = moisture_req.get('max', 90)

        # Estimate moisture from precipitation (simplified model)
        # Assume 50mm precip ~ 50% moisture
        estimated_moisture = min(100, precipitation * 0.8 + 20)

        # Use soil moisture if available, otherwise use estimated
        moisture_value = soil_moisture if soil_moisture is not None else estimated_moisture

        # Gaussian scoring around optimal
        if min_moisture <= moisture_value <= max_moisture:
            distance = abs(moisture_value - optimal)
            sigma = (max_moisture - min_moisture) / 4
            score = 100 * math.exp(-0.5 * (distance / sigma) ** 2)
        else:
            # Outside range
            if moisture_value < min_moisture:
                score = max(0, 50 - (min_moisture - moisture_value) * 2)
            else:
                score = max(0, 50 - (moisture_value - max_moisture) * 2)

        detail = {
            'precipitation_mm': precipitation,
            'estimated_moisture': round(estimated_moisture, 1),
            'optimal': optimal,
            'range': f"{min_moisture}-{max_moisture}%",
            'assessment': self._get_assessment(score)
        }

        return score, detail

    def _score_temperature(self, temp_data: Dict[str, float]) -> tuple:
        """
        Score temperature suitability.

        Args:
            temp_data: Dict with temperature_mean, temperature_min, temperature_max

        Returns:
            Tuple of (score, detail_dict)
        """
        temp_req = self.requirements.get('temperature', {})
        optimal = temp_req.get('optimal', 15)
        min_temp = temp_req.get('min', 8)
        max_temp = temp_req.get('max', 22)

        temp_mean = temp_data.get('temperature_mean', temp_data.get('temp_mean'))

        if temp_mean is None:
            # No temperature data
            return 50, {'assessment': 'No data available', 'value': None}

        # Gaussian scoring
        if min_temp <= temp_mean <= max_temp:
            distance = abs(temp_mean - optimal)
            sigma = (max_temp - min_temp) / 4
            score = 100 * math.exp(-0.5 * (distance / sigma) ** 2)
        else:
            # Outside acceptable range
            if temp_mean < min_temp:
                score = max(0, 50 - (min_temp - temp_mean) * 5)
            else:
                score = max(0, 50 - (temp_mean - max_temp) * 5)

        detail = {
            'value': round(temp_mean, 1),
            'optimal': optimal,
            'range': f"{min_temp}-{max_temp}°C",
            'assessment': self._get_assessment(score)
        }

        return score, detail

    def _score_season(self, current_month: int) -> tuple:
        """
        Score based on fruiting season.

        Args:
            current_month: Current month (1-12)

        Returns:
            Tuple of (score, detail_dict)
        """
        season_req = self.requirements.get('season', {})
        start_month = season_req.get('start_month', 1)
        end_month = season_req.get('end_month', 12)
        peak_month = season_req.get('peak_month', start_month)

        # Check if current month is in season
        in_season = False
        if start_month <= end_month:
            # Normal season (e.g., Mar-Jun)
            in_season = start_month <= current_month <= end_month
        else:
            # Wrapped season (e.g., Oct-Apr)
            in_season = current_month >= start_month or current_month <= end_month

        if current_month == peak_month:
            # Peak season
            score = 100
            status = "Peak season"
        elif in_season:
            # In season but not peak
            # Calculate distance from peak
            if start_month <= end_month:
                if current_month < peak_month:
                    distance = peak_month - current_month
                else:
                    distance = current_month - peak_month
            else:
                # Wrapped season - more complex
                if current_month >= start_month:
                    distance = (current_month - peak_month) if current_month >= peak_month else (peak_month - current_month + 12)
                else:
                    distance = abs(current_month - peak_month)

            # Score decreases with distance from peak
            score = max(70, 100 - distance * 10)
            status = "In season"
        else:
            # Off season - check if shoulder season (1 month before/after)
            shoulder = False
            if start_month <= end_month:
                if current_month == start_month - 1 or current_month == end_month + 1:
                    shoulder = True
            else:
                if current_month == end_month + 1 or current_month == start_month - 1:
                    shoulder = True

            if shoulder:
                score = 40
                status = "Shoulder season"
            else:
                score = 10
                status = "Off season"

        month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        detail = {
            'current_month': month_names[current_month] if 1 <= current_month <= 12 else str(current_month),
            'peak_month': month_names[peak_month] if 1 <= peak_month <= 12 else str(peak_month),
            'season': f"{month_names[start_month]}-{month_names[end_month]}",
            'status': status,
            'assessment': self._get_assessment(score)
        }

        return score, detail

    @staticmethod
    def _get_assessment(score: float) -> str:
        """Convert numerical score to text assessment."""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Very Good"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Fair"
        elif score >= 20:
            return "Poor"
        else:
            return "Unsuitable"
