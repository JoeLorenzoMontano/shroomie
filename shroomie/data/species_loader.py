"""Species database loader for mushroom requirements and scoring parameters."""

import json
import os
from typing import Dict, Any, List, Optional


class SpeciesDatabase:
    """Loads and manages mushroom species data from JSON database."""

    _species_data = None  # Cache for loaded species data
    _data_file = None

    @classmethod
    def _get_data_file_path(cls) -> str:
        """Get the path to the species database JSON file."""
        if cls._data_file is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            cls._data_file = os.path.join(current_dir, 'mushroom_species.json')
        return cls._data_file

    @classmethod
    def load_species_data(cls) -> Dict[str, Any]:
        """
        Load species database from JSON file.

        Returns:
            Dict containing all species data

        Raises:
            FileNotFoundError: If species database file doesn't exist
            json.JSONDecodeError: If JSON file is malformed
        """
        if cls._species_data is None:
            data_file = cls._get_data_file_path()

            if not os.path.exists(data_file):
                raise FileNotFoundError(
                    f"Species database not found at {data_file}. "
                    "Please ensure mushroom_species.json exists in the data directory."
                )

            with open(data_file, 'r') as f:
                cls._species_data = json.load(f)

        return cls._species_data

    @classmethod
    def get_species(cls, species_id: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific species by ID.

        Args:
            species_id: Species identifier (e.g., 'morels', 'chanterelles')

        Returns:
            Dict containing species data, or None if species not found
        """
        data = cls.load_species_data()
        return data.get(species_id)

    @classmethod
    def get_all_species(cls) -> List[str]:
        """
        Get list of all available species IDs.

        Returns:
            List of species identifiers
        """
        data = cls.load_species_data()
        return list(data.keys())

    @classmethod
    def get_all_species_info(cls) -> List[Dict[str, Any]]:
        """
        Get list of all species with their basic info (id, common_name, scientific_name).

        Returns:
            List of dicts with species info
        """
        data = cls.load_species_data()
        return [
            {
                'id': species_id,
                'common_name': species_data.get('common_name', species_id),
                'scientific_name': species_data.get('scientific_name', ''),
                'description': species_data.get('description', '')
            }
            for species_id, species_data in data.items()
        ]

    @classmethod
    def get_species_by_season(cls, month: int) -> List[str]:
        """
        Get species that fruit in the given month.

        Args:
            month: Month number (1-12, where 1 = January, 12 = December)

        Returns:
            List of species IDs that fruit in this month
        """
        data = cls.load_species_data()
        fruiting_species = []

        for species_id, species_data in data.items():
            season = species_data.get('requirements', {}).get('season', {})
            start_month = season.get('start_month')
            end_month = season.get('end_month')

            if start_month and end_month:
                # Handle seasons that wrap around the year (e.g., Oct-Apr)
                if start_month <= end_month:
                    # Normal season (e.g., Mar-Jun)
                    if start_month <= month <= end_month:
                        fruiting_species.append(species_id)
                else:
                    # Wrapped season (e.g., Oct-Apr means Oct-Dec and Jan-Apr)
                    if month >= start_month or month <= end_month:
                        fruiting_species.append(species_id)

        return fruiting_species

    @classmethod
    def clear_cache(cls):
        """Clear the cached species data (useful for testing or reloading)."""
        cls._species_data = None
