#!/bin/bash

TASK=$1
shift  #

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
    echo "Error: Unknown forecast task '$TASK'"
    echo "Usage: $0 {validate_inputs|forecast|report_only} [args...]"
    exit 1
    ;;
esac