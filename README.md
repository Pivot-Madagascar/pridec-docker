# PRIDE-C Forecast

A docker container to run the PRIDE-C Forecast Workflow

## Installation

## Usage

Don't forget to activate env before running.

```
source .venv/bin/activate
```
## Set Up Configs and `.env`

These files need to be updated for each data source and month.

## Update Input Data

Input data (climate,disease, geojson) is sourced from a DHIS2 instance. It needs to be updated following the instructions in `input/README.md`. 

To update them all run:

```
source .venv/bin/activate
python python-fetch-scripts/fetch_climate_input.py 
python python-fetch-scripts/fetch_disease_input.py 
python python-fetch-scripts/fetch_geojson_input.py 
```

This uses the ENV_VARIABLES stored in the `.env` file. It needs to be updated when using a different DHIS2 instance or dataSource

## Run forecasting workflow in docker

### To build the docker image and save output in `build.log`

This only needs to be done once.

```
docker build -t pridec-forecast -D --progress=plain . 2>&1 | tee build.log
```

### Run using the `test_config.json` file

This runs a faster version of the workflow that is just used for testing everything works

```
docker run --volume "$(pwd)/input:/app/input:ro" \
  --volume "$(pwd)/output:/app/output:rw" \
  --rm  pridec-forecast \
  --config "input/test_config.json"
```

### Run using the base `config.json`

This tests that all of the models work. but it does take longer

```
docker run --volume "$(pwd)/input:/app/input:ro" \
  --volume "$(pwd)/output:/app/output:rw" \
  --rm  pridec-forecast \
  --config "input/config.json"
```
