# PRIDE-C ETL Web API

This FastAPI application provides a REST API interface for PRIDE-C ETL operations.

## Setup

1. Build the Docker image:
   ```bash
   docker build -t pridec-etl-web ./web
   ```

2. Run the container with environment variables:
   ```bash
   docker run -p 8000:8000 --env-file .env pridec-etl-web
   ```

## Environment Variables

The API expects the same environment variables as the ETL service. Ensure your `.env` file contains:

- `DHIS_TOKEN`
- `DHIS_URL`
- `PARENT_OU`
- `OU_LEVEL`
- `DISEASE_CODE`
- `GEE_SERVICE_ACCOUNT`
- `GEE_VARIABLES`
- `PIVOT_URL`
- `PIVOT_TOKEN`
- And other required variables

## Endpoints

### GET /

Returns API information including version and documentation links.

### POST /import_gee

Runs the GEE import operation in the background.

**Response:** `{"status": "accepted", "message": "Import GEE task started in background"}`

### POST /import_pivot_com

Runs the Pivot COM import operation in the background.

**Response:** `{"status": "accepted", "message": "Import Pivot COM task started in background"}`

### POST /import_pivot_csb

Runs the Pivot CSB import operation in the background.

**Response:** `{"status": "accepted", "message": "Import Pivot CSB task started in background"}`

### POST /fetch_climate

Fetches climate data synchronously.

**Response:** `{"status": "success", "message": "Climate data fetched successfully"}`

**Error:** HTTP 500 on failure

### POST /fetch_disease

Fetches disease data synchronously.

**Response:** `{"status": "success", "message": "Disease data fetched successfully"}`

**Error:** HTTP 500 on failure

### POST /fetch_geojson

Fetches GeoJSON data synchronously.

**Response:** `{"status": "success", "message": "GeoJSON data fetched successfully"}`

**Error:** HTTP 500 on failure

### POST /build_analytics

Runs the analytics build operation in the background.

**Response:** `{"status": "accepted", "message": "Build analytics task started in background"}`

### POST /post_forecast

Posts forecast data synchronously.

**Response:** `{"status": "success", "message": "Forecast posted successfully"}`

**Error:** HTTP 500 on failure

### POST /calc_csb_alerts

Runs CSB alerts calculation in the background.

**Response:** `{"status": "accepted", "message": "Calculate CSB alerts task started in background"}`

### POST /update_key

Updates the PRIDE-C key synchronously.

**Response:** `{"status": "success", "message": "Key updated successfully"}`

**Error:** HTTP 500 on failure

### POST /forecast

Runs the forecast Docker container in the background.

**Parameters:**
- `config_path` (optional): Path to config file, default "input/config.json"
- `external_data_path` (optional): Path to external data file, default "input/external_data.csv"
- `climate_data_path` (optional): Path to climate data file, default "input/climate_data.json"
- `disease_data_path` (optional): Path to disease data file, default "input/disease_data.json"
- `orgUnit_poly_path` (optional): Path to GeoJSON file, default "input/orgUnit_poly.geojson"

**Response:** `{"status": "accepted", "message": "Forecast started", "job_id": "forecast_abc12345"}`

### GET /forecast/status/{job_id}

Returns the status of a forecast job.

**Response:** Job status object with status, timestamps, logs, and error messages if applicable.

## Documentation

- Interactive API docs: `http://localhost:8000/docs`
- ReDoc documentation: `http://localhost:8000/redoc`