# Shroomie Soil API

A tool for gathering environmental data relevant to mushroom cultivation and generating LLM prompts for mushroom growth analysis.

## Overview

This script accesses various APIs to collect environmental data about a location, including:

- Soil types, characteristics, and pH levels (SoilGrids API and OpenEPI API)
- Elevation data (Open-Meteo)
- Recent weather history (Open-Meteo)
- Tree cover and forest type estimation
- Tree species information with mushroom associations
- Grid analysis for comparing multiple nearby locations

## Installation

```bash
# Install as a package
pip install -e .

# Or install dependencies only
pip install -r requirements.txt

# Setup environment variables (optional)
cp .env.example .env
# Edit .env with your API keys and settings
```

## Code Structure

The code has been refactored into a modular structure:

```
shroomie/
├── __init__.py
├── apis/                 # API client implementations
│   ├── __init__.py
│   ├── forest_apis.py    # Forest and tree species APIs
│   ├── location_apis.py  # Location and elevation APIs
│   ├── soil_apis.py      # Soil data APIs
│   └── weather_apis.py   # Weather data APIs
├── cli/                  # Command-line interface
│   ├── __init__.py
│   ├── cli_parser.py     # Command-line argument parser
│   └── main.py           # Main entry point
├── models/               # Data models
│   ├── __init__.py
│   ├── coordinate.py     # Coordinate handling and conversions
│   └── soil_data.py      # Soil data models
└── utils/                # Utility functions
    ├── __init__.py
    ├── grid_utils.py     # Grid calculation utilities
    ├── map_generator.py  # Map generation utilities
    └── prompt_generator.py  # LLM prompt generation
```

## Usage

For detailed usage instructions:
```bash
python soil_api.py --help
```

### Basic Examples

```bash
# Basic usage with coordinates
python soil_api.py --lat 45.5434 --lon -123.4222 --prompt

# Complete data with mushroom type
python soil_api.py --lat 45.5434 --lon -123.4222 --weather --topo --trees --forest --prompt --mushroom-type "Chanterelle"

# Using location name instead of coordinates
python soil_api.py --location "Mount Hood, Oregon" --all --prompt

# Grid analysis (3x3 grid with points 1 mile apart)
python soil_api.py --lat 45.5434 --lon -123.4222 --all --prompt --grid --grid-size 3 --grid-distance 1.0

# Generate interactive map
python soil_api.py --lat 45.5434 --lon -123.4222 --all --map
```

### API Options

- `--soilgrids`: Query SoilGrids API for soil classification
- `--openepi`: Query OpenEPI API for soil type
- `--soil-properties`: Query OpenEPI API for detailed soil properties
- `--topo`: Add topographic data
- `--forest`: Add tree cover data
- `--trees`: Add tree species data with mushroom associations
- `--weather`: Add recent weather data
- `--all`: Query all available APIs
- `--prompt`: Generate an LLM prompt with all collected data

### Environment Variables

The following environment variables can be set in a `.env` file:

- `MAPBOX_TOKEN`: Access token for Mapbox terrain data
- `GFW_API_KEY`: API key for Global Forest Watch
- `OPENMETEO_API_KEY`: API key for Open-Meteo (optional, most endpoints work without authentication)
- `OSM_USER_AGENT`: User agent name for OpenStreetMap API calls
- `OSM_CONTACT_URL`: Contact URL for OpenStreetMap API calls
- `OSM_CONTACT_EMAIL`: Contact email for OpenStreetMap API calls

### Grid Analysis

- `--grid`: Generate a grid of points around the center coordinates
- `--grid-size`: Size of the grid (e.g., 3 for a 3x3 grid)
- `--grid-distance`: Distance between grid points in miles

### Map Generation

- `--map`: Generate an interactive HTML map with the data
- `--map-output`: Filename for the map (default: location_map.html)
- `--map-zoom`: Initial zoom level for the map (default: 10)

## Output

The script outputs a formatted prompt containing all the collected environmental data, ready to be used with an LLM for mushroom cultivation analysis. When using the grid feature, it analyzes multiple points and can generate a visual map of the area.