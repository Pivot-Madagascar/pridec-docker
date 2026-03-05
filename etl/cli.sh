#!/bin/sh
set -e

COMMAND="$1"
shift   

case "$COMMAND" in
import_gee)
echo "Importing climate variables from GEE to PRIDE-C instance"
python scripts/import_gee.py "$@"
;;

import_pivot_com)
echo "Importing historical COM data from Pivot instance to PRIDE-C instance"
python scripts/import_pivot_COM.py "$@"
;;

import_pivot_csb)
echo "Importing historical CSB data from Pivot instance to PRIDE-C instance"
python scripts/import_pivot_CSB.py "$@"
;;

fetch_climate)
echo "Downloading PRIDE-C climate data to input folder"
python scripts/fetch_pridec_climate.py "$@"
;;

fetch_disease)
echo "Downloading PRIDE-C historical disease data to input folder"
python scripts/fetch_pridec_disease.py "$@"
;;

fetch_geojson)
echo "Downloading PRIDE-C geojson polygons to input folder"
python scripts/fetch_pridec_geojson.py "$@"
;;

build_analytics)
echo "Building analytics tables on PRIDE-C instance"
python scripts/build_analytics.py "$@"
;;

post_forecast)
echo "Posting forecast to PRIDE-C instance"
python scripts/post_forecast.py "$@"
;;

*)
echo "Unknown command: $COMMAND"
echo "Usage: docker run etl <command> [args]"
echo ""
echo "Available commands:"
echo "  import_gee              - Import climate data from GEE to PRIDE-C instance"
echo "  import_pivot_com        - Import COM data from Pivot instance to PRIDE-C instance. For Pivot use only."
echo "  import_pivot_csb        - Import CSB data from Pivot instance to PRIDE-C instance. For Pivot use only."
echo "  fetch_climate           - Download climate data from PRIDE-C instance"
echo "  fetch_disease           - Download historical disease data from PRIDE-C instance"
echo "  fetch_geojson           - Download geojson polygons from PRIDE-C instance"
echo "  build_analytics         - Build the analytics table on PRIDE-C instance. This can take 10-15 minutes."
echo "  post_forecast           - Post forecast to PRIDE-C instance"
exit 1
;;
esac
