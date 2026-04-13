"""Seasonal calendar for mushroom fruiting periods."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from shroomie.data.species_loader import SpeciesDatabase


class SeasonalCalendar:
    """Manages seasonal mushroom fruiting data and timing."""

    MONTH_NAMES = [
        '', 'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]

    @classmethod
    def get_current_season_species(cls) -> List[Dict[str, Any]]:
        """
        Get species that are fruiting in the current month.

        Returns:
            List of dicts with species info (id, common_name, season info)
        """
        current_month = datetime.now().month
        return cls.get_species_by_season(current_month)

    @classmethod
    def get_species_by_season(cls, month: int) -> List[Dict[str, Any]]:
        """
        Get species that fruit in the given month.

        Args:
            month: Month number (1-12)

        Returns:
            List of dicts with species info
        """
        db = SpeciesDatabase()
        species_ids = db.get_species_by_season(month)

        result = []
        for species_id in species_ids:
            species_data = db.get_species(species_id)
            if species_data:
                season = species_data.get('requirements', {}).get('season', {})
                result.append({
                    'id': species_id,
                    'common_name': species_data.get('common_name', species_id),
                    'scientific_name': species_data.get('scientific_name', ''),
                    'season_start': season.get('start_month'),
                    'season_end': season.get('end_month'),
                    'peak_month': season.get('peak_month'),
                    'is_peak': month == season.get('peak_month')
                })

        return result

    @classmethod
    def get_season_calendar(cls) -> Dict[int, List[Dict[str, str]]]:
        """
        Get month-by-month fruiting calendar for all species.

        Returns:
            Dict mapping month number to list of species info
        """
        calendar = {month: [] for month in range(1, 13)}

        for month in range(1, 13):
            species_list = cls.get_species_by_season(month)
            for species in species_list:
                calendar[month].append({
                    'id': species['id'],
                    'common_name': species['common_name'],
                    'is_peak': species['is_peak']
                })

        return calendar

    @classmethod
    def is_peak_season(cls, species_id: str, month: Optional[int] = None) -> bool:
        """
        Check if given month is peak season for the species.

        Args:
            species_id: Species identifier
            month: Month number (1-12), defaults to current month

        Returns:
            True if it's peak season, False otherwise
        """
        if month is None:
            month = datetime.now().month

        db = SpeciesDatabase()
        species_data = db.get_species(species_id)

        if not species_data:
            return False

        season = species_data.get('requirements', {}).get('season', {})
        peak_month = season.get('peak_month')

        return month == peak_month

    @classmethod
    def is_in_season(cls, species_id: str, month: Optional[int] = None) -> bool:
        """
        Check if given month is within fruiting season for the species.

        Args:
            species_id: Species identifier
            month: Month number (1-12), defaults to current month

        Returns:
            True if in season, False otherwise
        """
        if month is None:
            month = datetime.now().month

        db = SpeciesDatabase()
        species_ids = db.get_species_by_season(month)

        return species_id in species_ids

    @classmethod
    def get_season_score(cls, species_id: str, month: Optional[int] = None) -> float:
        """
        Calculate seasonal score (0-100).

        Score meanings:
        - 100: Peak month
        - 80: Within fruiting window
        - 50: Shoulder season (1 month before/after)
        - 0: Out of season

        Args:
            species_id: Species identifier
            month: Month number (1-12), defaults to current month

        Returns:
            Seasonal score (0-100)
        """
        if month is None:
            month = datetime.now().month

        db = SpeciesDatabase()
        species_data = db.get_species(species_id)

        if not species_data:
            return 0

        season = species_data.get('requirements', {}).get('season', {})
        start_month = season.get('start_month')
        end_month = season.get('end_month')
        peak_month = season.get('peak_month')

        if not all([start_month, end_month, peak_month]):
            return 50  # Unknown season, give neutral score

        # Check if peak month
        if month == peak_month:
            return 100

        # Check if in season
        in_season = False
        if start_month <= end_month:
            # Normal season (e.g., Mar-Jun)
            in_season = start_month <= month <= end_month
        else:
            # Wrapped season (e.g., Oct-Apr)
            in_season = month >= start_month or month <= end_month

        if in_season:
            # Calculate distance from peak for scoring
            if start_month <= end_month:
                if month < peak_month:
                    distance = peak_month - month
                else:
                    distance = month - peak_month
            else:
                # Wrapped season - more complex
                if month >= start_month:
                    distance = (month - peak_month) if month >= peak_month else (peak_month - month + 12)
                else:
                    distance = abs(month - peak_month)

            # Score decreases with distance from peak
            return max(70, 100 - distance * 10)

        # Check if shoulder season (1 month before/after)
        shoulder = False
        if start_month <= end_month:
            shoulder = month == start_month - 1 or month == end_month + 1
        else:
            shoulder = month == end_month + 1 or month == start_month - 1

        if shoulder:
            return 40

        return 10  # Off season

    @classmethod
    def get_season_description(cls, species_id: str, month: Optional[int] = None) -> str:
        """
        Get human-readable season description for a species.

        Args:
            species_id: Species identifier
            month: Month number (1-12), defaults to current month

        Returns:
            Season description string
        """
        if month is None:
            month = datetime.now().month

        db = SpeciesDatabase()
        species_data = db.get_species(species_id)

        if not species_data:
            return "Unknown"

        season = species_data.get('requirements', {}).get('season', {})
        start_month = season.get('start_month')
        end_month = season.get('end_month')
        peak_month = season.get('peak_month')

        if not all([start_month, end_month, peak_month]):
            return "Season unknown"

        season_str = f"{cls.MONTH_NAMES[start_month]}-{cls.MONTH_NAMES[end_month]}"
        peak_str = f"Peak: {cls.MONTH_NAMES[peak_month]}"

        if cls.is_peak_season(species_id, month):
            return f"{season_str} ({peak_str}) - PEAK NOW! 🍄"
        elif cls.is_in_season(species_id, month):
            return f"{season_str} ({peak_str}) - In Season ✓"
        else:
            return f"{season_str} ({peak_str}) - Out of Season"

    @classmethod
    def get_whats_fruiting_now(cls) -> str:
        """
        Get a formatted string of what's fruiting in the current month.

        Returns:
            Formatted string with species and peak indicators
        """
        current_species = cls.get_current_season_species()

        if not current_species:
            return f"No species typically fruiting in {cls.MONTH_NAMES[datetime.now().month]}"

        current_month = datetime.now().month
        output = f"🍄 Fruiting in {cls.MONTH_NAMES[current_month]}:\n\n"

        # Separate peak and regular season
        peak_species = [s for s in current_species if s['is_peak']]
        regular_species = [s for s in current_species if not s['is_peak']]

        if peak_species:
            output += "**PEAK SEASON:**\n"
            for species in peak_species:
                output += f"  🌟 {species['common_name']}\n"
            output += "\n"

        if regular_species:
            output += "**In Season:**\n"
            for species in regular_species:
                output += f"  ✓ {species['common_name']}\n"

        return output
