# PRIDE-C Docker

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

This uses the ENV_VARIABLES stored in the `.env` file. It needs to be updated when using a different DHIS2 instance or dataSource following `.env.example`

## Run forecasting workflow in docker (not with compose)

I am in the process of updating this to a docker compose workflow.

Run this from within the `forecast` subdirectory.

### To build the docker image and save output in `build.log`

This only needs to be done once.

```
docker build -t pridec-forecast -D --progress=plain . 2>&1 | tee build.log
```

To run things interactively

```
docker run -it  pridec-forecast-workflow-fetch
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



## Run using docker compose

It needs to be run in order( fetch > forecast).

The directories input and output must already exist.

You must have already built the docker image using

```
docker compose build
docker compose build --no-cache #takes 15 minutes. assures it is clean
```

For `forecast`, input must contain a `config.json` file and `external_data.csv` file. They can have other names, but must be in the `input` directory to work with compose. If their name is different, it needs to be supplied via an argument to docker run

1. Run `fetch` service

```
docker compose --verbose run --rm fetch
```

2. Run `forecast` service

This uses a testing config. You must ensure that the `DISEASE_CODE` in `.env` matches the `disease_dataElement` in config (I will update this later to use the environment one).

```
docker compose --verbose run --rm forecast --config "input/test_config.json"
```

3. Clean up unused containers

```
docker compose down --remove-orphans
```

4. To run a service interactively

```
docker compose run --rm --entrypoint "/bin/bash" <service-name>
```

## Helpful testing code

I made a dev compose file `compose-dev.yml`. It can be used via:

```
docker compose --file compose-dev.yaml run fetch
```

change this to just one service at once, for example.

Some helpful things for debugging. Note that I should never actually use `docker compose up` because it will run both services as once, and we want them to run sequentially. I will need to write a documentation/script to do this.

```
docker compose run --rm --entrypoint "/bin/bash" <service-name> #interactive shell

docker compose --verbose run <service-name>

docker compose logs -f <service-name>

docker image inspect <service-name>

docker run <service-name> --help

```

Add this to docker compose to stop it from immediately stopping the app:

```
command: ["sleep", "3600"]
```

To rebuild full docker compose image from scratch (takes 15 minutes)

```
docker compose build --no-cache
```