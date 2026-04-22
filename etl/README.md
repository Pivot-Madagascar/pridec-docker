# PRIDE-C ETL Docker IService

This docker image is used to run the ETL functions of the PRIDE-C workflow. This includes processes like importing and exporting data from DHIS2, running environmental data treatment in Google Earth Engine, and DHIS2 admin tasks relevant to PRIDE-C. This image is part of a docker compose suit of services described in this [github repo](https://github.com/Pivot-Madagascar/pridec-docker). 

# Usage 

## Building Service

The service should be built using `docker compose` v2. 

```
curl -o compose.yaml https://raw.githubusercontent.com/Pivot-Madagascar/pridec-docker/refs/heads/main/compose.yaml
docker compose build etl
```

You can also build the service locally from the github repo, downloaded via `git`. To build the service locally run:

```
git clone https://github.com/Pivot-Madagascar/pridec-docker.git
cd pridec-docker
docker compose -f compose-build.yaml build etl
```

Note that the directory structure below must be added to the `pridec-docker` folder to run if it is built this way.

## Directory Structure

The service requires the following file structure:

```
project/
├── input/
├── output/
├── .env
├── .gee-private-key.json
└── compose.yaml

```

The `input` directory will contain data fetched from DHIS2 and is also where model inputs for the `forecast` service are stored.

The `output` directory will contain the outputs of the `forecast` service. If you wish to post forecasts, they must be saved as `output/forecast.json`.

## Environmental Variables

The `.env` file contains tokens and URLs needed for accessing the API endpoints. By default, `.env` is included in the service if it is found in the project directory. An alternate can be provided to the docker image using the `---env-from-file` flag when running.  The `.env` file should follow this template:

```
DHIS_URL = 'http://your-dhis-url/'
DHIS_TOKEN = "d2pat_your-token"

DRYRUN = 'False'
LOG_LEVEL = 'DEBUG' 

PARENT_OU="orgUnitid" #id orgUnit that contains orgUnits of interest
DISEASE_CODE="pridec_historic_diseaseCode" #for fetching disease data
OU_LEVEL='6' #hierarchical level of orgUnits, numeric

GEE_PROJECT='your-project-name'
GEE_SERVICE_ACCOUNT='your-account@your-project.iam.gserviceaccount.com'

#only needed for import_pivot data services
PIVOT_URL="pivot-prod-url"
PIVOT_TOKEN="d2pat_your-pivot-token"
```

Individual environmental variables can also be provided to the docker service via the `--env` flag when running.

## Available commands

The available commands can be queried by running:

```
docker compose run etl --help
```

It is recommended to run commands with the `--rm` flag to prevent orphaned containers.

# General PRIDE-C workflow

## 1. Import health and climate data into PRIDE-C instance

### 1.1 `import_gee` service to import GEE climate varables into DHIS2 instance [once per month]

This requires having a `.gee-private-key.json` in the root directory as well as a `GEE_SERVICE_ACCOUNT` in `.env`. There is one climate variable that is specific to Ifanadiana (`pridec_climate_floodedRice`), but could be applied to other regions if they provide a polygon of ricefields.

```
docker compose run --rm etl import_gee
```

In order for this data to be available via `analytics` calls, the Analytics Tables must be rebuilt:

```
docker compose run --rm etl build_analytics
```

### 1.2  `import_pivot` service to import Madagascar specific data (Pivot-only) [once per month]

This is an optional service to only be run on the Pivot PRIDE-C instance used by Pivot. It creates the `pridec_historical_` variables that are needed for predictions. This is needed because there is some cleaning and formatting we do with the raw `dataElements` to have high quality variables to predict.

```
docker compose run --env-from-file .env --rm etl import_pivot_com
docker compose run --env-from-file .env --rm etl import_pivot_csb
#analytics tables should be rebuilt after this
docker compose run --env-from-file .env --rm etl build_analytics
```

## 2. Forecast individual `dataElements` via `forecast`

The forecast step should be run for each dataElement being predicted. Its steps are:

1. Fetching the necessary climate, disease, and geospatial data from teh PRIDE-C instance
2. Using the data in the `forecast` workflow (this is available in a seperate docker image [here](https://hub.docker.com/r/mvevans89/pridec_forecast))
3. `POST`ing the forecasts to the PRIDE-C instance

### 2.1. `fetch` service to download climate, disease, and geospatial data

This uses the ENV_VARIABLES stored in the `.env` file. It needs to be updated when using a different DHIS2 instance or dataSource following `.env.example`. This step is run for every `dataElement` that you wish to predict.

```
docker compose run --env-from-file .env --rm etl fetch_climate
docker compose run --env-from-file .env --rm etl fetch_disease
docker compose run --env-from-file .env --rm etl fetch_geojson
```

### 2.2. `forecast` service to create predictions (uses seperate docker image)

Running the forecast requires a seperate docker image [pridec_forecast][here](https://hub.docker.com/r/mvevans89/pridec_forecast).

For `forecast`, input must contain a `config.json` file and `external_data.csv` file. They can have other names, but must be in the `input` directory to work with compose. If their name is different, it needs to be supplied via an argument to `docker compose run`, as in the below example

```
docker compose run --rm pridec_forecast --config "input/config.json"
```

You should now inspect the model validation report in `output/forecast_report.html`. If everything seems okay, proceed to step `2c` to import the forecast into the PRIDE-C instance.

### 2.3. `POST` the forecast to the PRIDE-C instance

Once the forecast has been validated, it can be posted to the instance.

```
docker compose run --env-from-file .env --rm etl post_forecast
```

## 3. PRIDE-C System Updates

Once all the forecasts have been posted, there are several steps to update the rest of the PRIDE-C system. They are all run via one line commands to the `pridec_etl` image.

1. Calculate and post the number of health centers on alert
2. Build the analytics tables
3. Update the PRIDE-C dataStore key

### 3.1. Calcuate the CSB on alert

Thie estimates the number of health centers expected to see more cases than the three year average for that season for each disease. It queries the `analytics` endpoint and so requries the analytics tables to be built first.

```
docker compose run --env-from-file .env --rm etl build_analytics
docker compose run --env-from-file .env --rm etl calc_CSB_alerts
```

### 3.2. Build the analytics tables

Because the PRIDE-C app accessed data via a call to analytics, the tables must be built for the updated data to be available:

```
docker compose run --env-from-file .env --rm etl build_analytics
```

### 3.3. Update the PRIDE-C dataStore key

This key is used by the application cache to trigger an update of data in a user's cache after the monthly update:

```
docker compose run --env-from-file .env --rm etl update_key
```


