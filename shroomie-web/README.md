# Shroomie Web

A web interface for the Shroomie mushroom foraging analysis tool.

## Overview

This web application provides a user-friendly interface to the Shroomie tool, allowing users to:

- Input coordinates or location names
- Run soil and environmental analysis for mushroom foraging
- View detailed reports on mushroom suitability
- Perform grid analysis to compare nearby locations

## Setup

### Prerequisites

- Docker and Docker Compose
- The Shroomie package (should be in the parent directory)

### Environment Variables

Copy your `.env` file from the parent directory or create a new one:

```bash
cp ../.env ./.env
```

Make sure it contains the necessary API keys:
- `GFW_API_KEY`: Global Forest Watch API key
- `OPENMETEO_API_KEY`: Open-Meteo API key (if needed)
- `OSM_USER_AGENT`, `OSM_CONTACT_URL`, `OSM_CONTACT_EMAIL`: OpenStreetMap credentials

### Running the Application

1. Start the application with Docker Compose:
   ```bash
   docker-compose up --build
   ```

2. Access the web interface at [http://localhost:5000](http://localhost:5000)

## Usage

1. Choose input method: Coordinates or Location Name
2. Enter the required information
3. (Optional) Enable grid analysis to examine a grid of points around the specified location
4. Click "Analyze" to run the analysis
5. View the results in the output panel

## Development

To make changes to the web interface:

1. Modify files in the `app` directory
2. Rebuild and restart the container:
   ```bash
   docker-compose down
   docker-compose up --build
   ```