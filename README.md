# PRIDE-C Docker

A docker container to run the PRIDE-C Forecast Workflow

## Requirements

- [docker compose](https://docs.docker.com/compose/install/)
- 3.5 GB storage space for docker image
- RAM requirements depend on the number of orgUnits, the models used in a forecast, and your own docker configurations. It ranges from 1 GB for 20 orgUnits using the `test_config.json` configuration to the smallest models to 2.5 GB for 200 orgUnits fitting all five models. You can also set the limit manually within the individual `Dockerfile`s or in `compose-auto.yaml` or `compose.yaml` files following instructions [here](https://docs.docker.com/engine/containers/resource_constraints/).

## Installation

### Download

Download via `curl`
```
curl -L -O https://github.com/Pivot-Madagascar/pridec-docker/archive/refs/head/main.tar.gz | tar xz 
cd pridec-docker
```

Download via `git`
```
git clone https://github.com/Pivot-Madagascar/pridec-docker.git
cd pridec-docker
```

### Automatic install via `install.sh` (recommended, Mac/Linux only)

This shell script will install the PRIDE-C Docker app and make it available via the command `pridec`. This will allow you to access the pridec services from anywhere using `pridec` instead of `docker compose`.

Edit the file called `pridec` in the pridec-docker directory. It should contain the following (only `COMPOSE_DIR` needs to be updated):

```
#!/bin/bash

COMPOSE_DIR="/path/to/pridec-docker" #update to be path to installed repo
HOST_PWD="$(pwd)"
HOST_PWD="$HOST_PWD" docker compose -f "$COMPOSE_DIR/compose-auto.yaml" "$@"
```

Run the install script. This will take 15-20 minutes depending on your internet connection.

```

chmod +x install.sh
./install.sh
```

Check it is installed correctly:

```
pridec config
which pridec
```

### Manual install via `docker compose build`

You can also use the application directly via `docker compose`. This will take about 15 minutes the first time it is run.

```
docker compose build -f compose-prod.yaml
docker compose build -f compose-prod.yaml --no-cache #takes 15 minutes. ensures it is clean
```

To access the PRIDE-C services for a manual install, you will need to use the `docker compose run` call to access the `etl` and `forecast` services.

## Usage (auto install)

An example of an automated workflow using a shell script is available in the [pridec-pivot-update repo](https://github.com/Pivot-Madagascar/pridec-pivot-update/tree/main).

The primary steps are:

1. Create a project directory for the dataElement you wish to predict
2. Create `input` and `output` subdirectories
3. Copy your `config.json` and `external_data.csv` into the `input` directory. See example files [here](https://github.com/Pivot-Madagascar/pridec-pivot-update/tree/main/forecast_assets).
4. Create a `.env` file following `.env.example` in the `pridec-docker` directory
5. Run the full workflow from the project directory. Some example code is below:

Calling `pridec` will launch a one-off container, loading the .env file and exiting afterwards. It is equivalent to `docker compose -f "compose.yaml" run --env-from-file .env --rm` and can take arguments to each service. Run `pridec -h` for more details.

```
#import data from GEE into your DHIS2 instance (this only needs to be done once per month)
pridec --env DRYRUN="true" etl import_gee

#import data from Pivot instance (this is specific to Ifanadiana and Pivot), run once per month
pridec --env-from-file .env --env DRYRUN=true --rm etl import_pivot_com
pridec --env-from-file .env --env DRYRUN=true --rm etl import_pivot_csb

#run analytics table before fetching
pridec --env-from-file .env --env DRYRUN=true --rm etl build_analytics

pridec --env-from-file .env --env DRYRUN=true --rm etl fetch_climate
pridec --env-from-file .env --env DRYRUN=true --rm etl fetch_disease
pridec --env-from-file .env --env DRYRUN=true --rm etl fetch_geojson

#allows you to keep the same URL and TOKEN and just change specific envvars
pridec --env-from-file .env --env DRYRUN=true --env OU_LEVEL='5' --rm etl fetch_climate
pridec --env-from-file .env --env DRYRUN=true --env OU_LEVEL='5' --rm etl fetch_geojson
pridec --env-from-file .env --env DRYRUN="false" --env DISEASE_CODE="pridec_historic_CSBMalaria" --env OU_LEVEL='5' --rm etl fetch_disease

#config file can be changed for each disease. default is config.json
pridec --rm forecast --config "input/config_malaria.json" --external_data "input/external_data_csb.csv"

#YOU SHOULD INSPECT output/forecast_report.html NOW

#PAY ATTENTION HERE AS THIS WILL CHANGE YOUR INSTANCE. update DRYRUN as needed
pridec --env-from-file .env --env DRYRUN=true --rm etl post_forecast

#to run analytics table
pridec --env-from-file .env --env DRYRUN=true --rm etl build_analytics
#update key and CSB on alert
pridec --env-from-file .env --env DRYRUN="false" --rm etl calc_CSB_alerts
pridec --env-from-file .env --env DRYRUN="false" --rm etl update_key
pridec --env-from-file .env --env DRYRUN=true --rm etl build_analytics

pridec down --remove-orphans
```

## Usage (manual install)

If it is manually installed, these steps need to be run from the `pridec-docker` project directory.

This needs to be run in order (import > fetch > forecast > post).

The directories `input` and `output` must already exist in the `pridec-docker` directory. You will receive an error if that is not the case.

The `.env` file must be updated for your use case, or the ENV_VARIABLES provided directly to `docker compose run`.

Most tasks are run through the `etl` image, which manages all of the sending and formatting of data from GEE, the Pivot DHIS2 instance, and the PRIDE-C DHIS2 instance. The forecasting step relies on `R`, which is a larger docker image and contained in its own docker image, `forecast`.

### 1. Import health and climate data into PRIDE-C instance

#### 1.1 `import_gee` service to import GEE climate varables into DHIS2 instance [once per month]

This requires having a `.gee-private-key.json` in the root directory as well as a `GEE_SERVICE_ACCOUNT` in `.env`. There is one climate variable that is specific to Ifanadiana (`pridec_climate_floodedRice`), but could be applied to other regions if they provide a polygon of ricefields.

```
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl import_gee
```

In order for this data to be available via `analytics` calls, the Analytics Tables must be rebuilt:

```
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl build_analytics
```

#### 1.2  `import_pivot` service to import Madagascar specific data (Pivot-only) [once per month]

This is an optional service to only be run on the Pivot PRIDE-C instance used by Pivot. It creates the `pridec_historical_` variables that are needed for predictions. This is needed because there is some cleaning and formatting we do with the raw `dataElements` to have high quality variables to predict.

```
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl import_pivot_com
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl import_pivot_csb
#analytics tables should be rebuilt after this
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl build_analytics
```

### 2. Forecast individual `dataElements` via `forecast`

The forecast step should be run for each dataElement being predicted. Its steps are:

1. Fetching the necessary climate, disease, and geospatial data from teh PRIDE-C instance
2. Using the data in the `forecast` workflow
3. `POST`ing the forecasts to the PRIDE-C instance

#### 2.1. `fetch` service to download climate, disease, and geospatial data

This uses the ENV_VARIABLES stored in the `.env` file. It needs to be updated when using a different DHIS2 instance or dataSource following `.env.example`. This step is run for every `dataElement` that you wish to predict.

```
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl fetch_climate
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl fetch_disease
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl fetch_geojson
```

#### 2.2. `forecast` service to create predictions.

For `forecast`, input must contain a `config.json` file and `external_data.csv` file. They can have other names, but must be in the `input` directory to work with compose. If their name is different, it needs to be supplied via an argument to `docker run`, as in the below example

```
docker compose run --rm forecast --config "input/config.json" --external_data "input/external_data_fkt.csv"
```

You should now inspect the model validation report in `output/forecast_report.html`. If everything seems okay, proceed to step `2c` to import the forecast into the PRIDE-C instance.

#### 2.3. `POST` the forecast to the PRIDE-C instance

Once the forecast has been validated, it can be posted to the instance.

```
docker compose run --env-from-file .env --rm etl post_forecast
```

### 3. PRIDE-C System Updates

Once all the forecasts have been posted, there are several steps to update the rest of the PRIDE-C system. They are all run via one line commands to the `etl` image.

1. Calculate and post the number of health centers on alert
2. Build the analytics tables
3. Update the PRIDE-C dataStore key

#### 3.1. Calcuate the CSB on alert

Thie estimates the number of health centers expected to see more cases than the three year average for that season for each disease. It queries the `analytics` endpoint and so requries the analytics tables to be built first.

```
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl build_analytics
#wait until this has completed before calculating the health centers on alert
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl calc_CSB_alerts
```

#### 3.2. Build the analytics tables

Because the PRIDE-C app accessed data via a call to analytics, the tables must be built for the updated data to be available:

```
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl build_analytics
```

#### 3.3. Update the PRIDE-C dataStore key

This key is used by the application cache to trigger an update of data in a user's cache after the monthly update:

```
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl update_key
```

### 6. Clean up unused containers (optional)

If an image is run withou the `--rm` flag, it can create orphaned containers. Clean those up by running:

```
docker compose down --remove-orphans
```

## Uninstall

To uninstall the automatic installation, first remove the symlinked application:

```
rm -f $HOME/bin/pridec
which pridec
```

This should return `pridec not found` or nothing.

Stop all containers and rm images associated with `pridec`:

```
docker container ps -a
docker container rm <CONTAINER-ID>


docker image ls
docker image rm <IMAGE-ID>
```

Delete the `pridec-docker` directory that you had initially downloaded.

## Helpful commands for testing and debugging

**Never use `docker compose up` because it will run all services at once, rather than sequentially.** 

```
docker compose run --rm --entrypoint "/bin/bash" <service-name> #interactive shell

docker compose --verbose run <service-name>

docker compose logs -f <service-name>

docker image inspect <service-name>

docker run <service-name> --help

```

To rebuild full docker compose image from scratch (takes 15 minutes)

```
docker compose build --no-cache
```