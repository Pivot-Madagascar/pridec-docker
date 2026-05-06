#!/bin/sh
set -e

COMMAND="$1"
shift || true  

# Function to print usage/help
print_usage() {
    echo "Usage: docker compose run etl <command> [args]"
    echo ""
    echo "Available commands:"
    echo "  --help, -h           - View usage documentation."
    echo "  import_gee           - Import climate data from GEE to PRIDE-C instance."
    echo "  import_pivot_com     - Import historical COM data from Pivot instance to PRIDE-C instance. Pivot use only."
    echo "  import_pivot_csb     - Import historical CSB data from Pivot instance to PRIDE-C instance. Pivot use only."
    echo "  fetch_climate        - Download climate data from PRIDE-C instance to input folder."
    echo "  fetch_disease        - Download historical disease data from PRIDE-C instance to input folder."
    echo "  fetch_geojson        - Download geojson polygons from PRIDE-C instance to input folder."
    echo "  post_forecast        - Post forecast to PRIDE-C instance."
    echo "  build_analytics      - Build the analytics table on PRIDE-C instance. This can take 10-15 minutes."
    echo "  calc_CSB_alerts      - Calculate the number of CSB on alert for this month and post to PRIDE-C instance."
    echo "  update_key           - Update the datastore key used to trigger PRIDE-C cache reset every month." 
    echo "                         Run at the end of all updates."
    echo ""
    echo "Examples:"
    echo "  docker compose run etl fetch_geojson"
    echo "  docker compose run --env-from-file .env --env DRYRUN='true' etl fetch_climate"
    echo ""
    echo "Notes:"
    echo "- Automatically uses .env file in current directory." 
    echo "  Specify another with the --env-from-file flag."
    echo "  Individual environmental variables can be specified via --env."
}

# Show help if no command or -h/--help
if [ -z "$COMMAND" ] || [ "$COMMAND" = "-h" ] || [ "$COMMAND" = "--help" ]; then
    print_usage
    exit 0
fi

case "$COMMAND" in
import_gee)
    PYTHONPATH=/app python -m scripts.import_gee "$@"
    ;;

import_pivot_com)
    PYTHONPATH=/app python -m scripts.import_pivot_COM "$@"
    ;;

import_pivot_csb)
    PYTHONPATH=/app python -m scripts.import_pivot_CSB "$@"
    ;;

fetch_climate)
    PYTHONPATH=/app python -m scripts.fetch_pridec_climate "$@"
    ;;

fetch_disease)
    PYTHONPATH=/app python -m scripts.fetch_pridec_disease "$@"
    ;;

fetch_geojson)
    PYTHONPATH=/app python -m scripts.fetch_pridec_geojson "$@"
    ;;

build_analytics)
    PYTHONPATH=/app python -m scripts.build_analytics "$@"
    ;;

post_forecast)
    PYTHONPATH=/app python -m scripts.post_forecast "$@"
    ;;

calc_CSB_alerts)
    PYTHONPATH=/app python -m scripts.calc_CSB_alerts "$@"
    ;;

update_key)
    PYTHONPATH=/app python -m scripts.update_pridec_key "$@"
    ;;

*)
    echo "Unknown command: $COMMAND"
    echo ""
    print_usage
    exit 1
    ;;
esac