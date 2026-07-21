#!/bin/bash
set -e

TASK=$1
shift  #

print_usage() {
    echo "Usage: docker compose run [docker compose args] forecast <task> [task args]"
    echo ""
    echo "Available tasks:"
    echo "  --help, -h           - View usage documentation."
    echo "  validate_inputs      - Validate input files for forecasting in input/ folder. "
    echo "                         Saves validated inputs as input/config_valid.json, input/input_valid.json, and input/polygon_valid.geojson."
    echo "                         See 'docker compose run forecast validate_inputs --help' for available arguments."
    echo "  forecast             - Run statistical forecast workflow and create report. Requires validated inputs."
    echo "                         See 'docker compose run forecast forecast --help' for available arguments."
    echo "  report_only          - Create HTML report from finished forecast. Used if forecast runs successfully but error on report creation."
    echo "                         Requires output/ to contain config.json, forecast.json, input_data.json, input_data.Rdata, and polygon.geojson."

    echo "Examples:"
    echo "  docker compose run forecast validate_inputs"
    echo "  docker compose run --env-from-file .env --env forecast --polygon_valid=input/polygon_valid.geojson"
    echo "  docker compose run report_only"
    echo ""
    echo "Notes:"
    echo "- Automatically uses .env file in current directory." 
    echo "  Specify another with the --env-from-file flag."
    echo "  Individual environmental variables can be specified via --env."
}

if [ -z "$TASK" ] || [ "$TASK" = "-h" ] || [ "$TASK" = "--help" ]; then
    print_usage
    exit 0
fi

case "$TASK" in
  "validate_inputs")
    exec Rscript /app/01_validate-inputs.R "$@"
    ;;
  "forecast")
    exec Rscript /app/02_forecast.R "$@"
    ;;
  "report_only")
    exec Rscript /app/03_create-report.R "$@"
    ;;
  *)
    echo "Error: Unknown forecast task: '$TASK'"
    echo ""
    print_usage
    exit 1
    ;;
esac