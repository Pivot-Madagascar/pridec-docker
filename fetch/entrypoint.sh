#!/bin/bash
set -e  # exit on error

python scripts/fetch_climate_input.py
python scripts/fetch_disease_input.py
python scripts/fetch_geojson_input.py