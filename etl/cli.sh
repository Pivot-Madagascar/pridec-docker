#!/bin/sh
set -e

TASK="$1"
shift || true  

# Function to print usage/help
print_usage() {
    echo "Usage: docker compose run [docker compose args] etl <task> [task args]"
    echo ""
    echo "Available tasks:"
    echo "  --help, -h           - View usage documentation."
    echo "  import_gee           - Import climate data from GEE to PRIDE-C instance. Can supply variables to import as env var GEE_VARIABLES."
    echo "  import_pivot_com     - Import historical COM data from Pivot instance to PRIDE-C instance. Pivot use only."
    echo "  import_pivot_csb     - Import historical CSB data from Pivot instance to PRIDE-C instance. Pivot use only."
    echo "  fetch_climate        - Download climate data from PRIDE-C instance to input folder."
    echo "  fetch_disease        - Download historical disease data from PRIDE-C instance to input folder."
    echo "  fetch_geojson        - Download geojson polygons from PRIDE-C instance to input folder."
    echo "  validate_inputs      - Validate input files for forecasting in input/ folder. "
    echo "                         Saves validated inputs as input/config_valid.json, input/input_valid.json, and input/polygon_valid.geojson."
    echo "                         See 'docker compose run etl validate_inputs --help' for available arguments."
    echo "  calc_CSB_alerts      - Calculate the number of CSB on alert for this month and post to PRIDE-C instance."
    echo "  calc_orgUnit_alerts  - Calculate the number of orgUnits on alert and save as output/alerts.json. More generalizable version of calc_CSB_alerts."
    echo "  post_forecast        - Post forecast to PRIDE-C instance."
    echo "  build_analytics      - Build the analytics table on PRIDE-C instance. This can take 10-15 minutes."
    echo "  update_key           - Update the datastore key used to trigger PRIDE-C cache reset every month." 
    echo "                         Run at the end of all updates."
    echo ""
    echo "Examples:"
    echo "  docker compose run etl fetch_geojson"
    echo "  docker compose run --env-from-file .env --env DRYRUN='true' etl fetch_climate"
    echo "  docker compose run --env GEE_VARIABLES='pridec_climate_temperatureMean,pridec_climate_windspeed' --env LOG_LEVEL='INFO' etl import_gee"
    echo ""
    echo "Notes:"
    echo "- Automatically uses .env file in current directory." 
    echo "  Specify another with the --env-from-file flag."
    echo "  Individual environmental variables can be specified via --env."
}

# Show help if no command or -h/--help
if [ -z "$TASK" ] || [ "$TASK" = "-h" ] || [ "$TASK" = "--help" ]; then
    print_usage
    exit 0
fi

case "$TASK" in
import_gee)
    python scripts/import_gee.py "$@"
    ;;

import_pivot_com)
    python scripts/import_pivot_COM.py "$@"
    ;;

import_pivot_csb)
    python scripts/import_pivot_CSB.py "$@"
    ;;

fetch_climate)
    python scripts/fetch_pridec_climate.py "$@"
    ;;

fetch_disease)
    python scripts/fetch_pridec_disease.py "$@"
    ;;

fetch_geojson)
    python scripts/fetch_pridec_geojson.py "$@"
    ;;

build_analytics)
    python scripts/build_analytics.py "$@"
    ;;

validate_inputs)
    python scripts/validate_inputs.py "$@"
    ;;

post_forecast)
    python scripts/post_forecast.py "$@"
    ;;

calc_CSB_alerts)
    python scripts/calc_CSB_alerts.py "$@"
    ;;

calc_orgUnit_alerts)
    python scripts/calc_orgUnit_alerts.py "$@"
    ;;

update_key)
    python scripts/update_pridec_key.py "$@"
    ;;

*)
    echo "Unknown etl task: $TASK"
    echo ""
    print_usage
    exit 1
    ;;
esac