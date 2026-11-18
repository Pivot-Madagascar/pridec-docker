#!/bin/bash
set -e

# Simple end2end test for etl cli functionality, to be built out into true tests with mock API later.
# Written for use by Michelle using her local setup, this probably won't work on your machine.

# to run:
# create env file following env example. name it .env.testcli
# start up local d2 instance: d2 cluster up pridec_202607
# manually run each of hte following steps and check it is okay

#build etl image and ensure it is newest version
docker compose -f compose-build.yaml build etl

docker compose run --env-from-file .env.docker --rm etl -h

docker compose run --env-from-file .env.docker --env DRYRUN="true" --rm etl import_gee
docker compose run --env-from-file .env.docker --rm etl import_pivot_com
docker compose run --env-from-file .env.docker --rm etl import_pivot_csb

docker compose run --env-from-file .env.docker --rm etl build_analytics

#check DISEASECODE in .env.docker
docker compose run --env-from-file .env.docker --rm etl fetch_climate
docker compose run --env-from-file .env.docker --rm etl fetch_disease
docker compose run --env-from-file .env.docker --rm etl fetch_geojson
#copy external_data and config from assets and past into inputs

docker compose run --env-from-file .env.docker --rm etl validate_inputs

docker compose run --rm forecast -h
docker compose run --env-from-file .env.docker --rm forecast forecast

docker compose run --env-from-file .env.docker --env ALERT_NAME="COMRespinfVigilance" --rm etl calc_orgUnit_alerts

#will error if it doesn't match CSB alert name
docker compose run --env-from-file .env.docker --rm etl post_forecast


