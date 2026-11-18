# PRIDE-C ETL Docker Service

This docker image is used to run the ETL functions of the PRIDE-C workflow. This includes processes like importing and exporting data between DHIS2 instances, running environmental data treatment in Google Earth Engine, and DHIS2 admin tasks relevant to PRIDE-C. This image is part of a docker compose suite of services described in this [github repo](https://github.com/Pivot-Madagascar/pridec-docker).

# Workflow order

Tasks are run via `docker compose run --rm etl <task>`. A typical monthly update runs in this order:

| Step | Task | Frequency | Prerequisite | Pivot-only | Changes remote instance? |
|------|------| ----------|---------------------|:----------:|:------------------------:|
| 1 | [`import_gee`](#import_gee) | Monthly | None | No | Yes |
| 2 | [`import_pivot_com`](#import_pivot_com), [`import_pivot_csb`](#import_pivot_csb) | Monthly | Yes | Yes |
| 3 | [`build_analytics`](#build_analytics) | Monthly | After steps 1-2, so new data is available via `analytics`. Completes `import` step. | No | Yes |
| 4 | [`fetch_climate`](#fetch_climate), [`fetch_disease`](#fetch_disease), [`fetch_geojson`](#fetch_geojson) | Once per `dataElement` run. | Complete `import` steps. | No | No |
| 5 | [`validate_inputs`](#validate_inputs) | Once per `dataElement` run. | After data has been fetched and `input/config.json` exists. | No | No |
| 6 | `forecast` (separate image, see [below](#forecast-separate-image)) | Once per `dataElement` run. | After inputs are validated. | No | No |
| 7 | [`calc_orgUnit_alerts`](#calc_orgunit_alerts) | Once per `dataElement` run (CSB only). | After step 6 (needs `output/forecast.json`). | No | No (writes `output/alerts.json`) |
| 8 | [`post_forecast`](#post_forecast) | Once per `dataElement` run. | Final step in forecast.Requires validated forecast report. | No | Yes |
| 9 | [`build_analytics`](#build_analytics) | Monthly | After all `dataElement` runs have been completed. | No | Yes |
| 10 | [`update_key`](#update_key) | Monthly | Last step of monthly update .| No | Yes |


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

The `.env` file contains tokens and URLs needed for accessing the API endpoints. By default, `.env` is included in the service if it is found in the project directory. An alternate can be provided to the docker image using the `--env-from-file` flag when running. The `.env` file should follow this template:

```
DHIS_URL = 'http://your-dhis-url/'
DHIS_TOKEN = "d2pat_your-token"

DRYRUN = 'False'
LOG_LEVEL = 'DEBUG'

PARENT_OU="orgUnitid" #id orgUnit that contains orgUnits of interest
DISEASE_CODE="pridec_historic_diseaseCode" #for fetching disease data
OU_LEVEL='6' #hierarchical level of orgUnits, numeric

#only needed for calc_orgUnit_alerts
ALERT_NAME="name of alert dataElement"
ALERT_FOCAL_DATE="202601" #optional, YYYYMM, defaults to today

GEE_SERVICE_ACCOUNT='your-account@your-project.iam.gserviceaccount.com'
#optional, empty will import all variables
GEE_VARIABLES="pridec_climate_var1,pridec_climate_var2"

#only needed for import_pivot data services
PIVOT_URL="pivot-prod-url"
PIVOT_TOKEN="d2pat_your-pivot-token"
```

| Variable | Used by | Notes |
|----------|---------|-------|
| `DHIS_URL`, `DHIS_TOKEN` | All tasks that talk to the PRIDE-C instance. | Required. A trailing `/` on the URL is removed. |
| `DRYRUN` | Tasks that write to the instance (`import_*`, `post_forecast`, `calc_CSB_alerts`, `update_key`) | **Defaults to dry run.** Any value other than `false` (case-insensitive), including unset, means no data is written. Set `DRYRUN='false'` for a real run. |
| `LOG_LEVEL` | All tasks | Default `INFO`. |
| `PARENT_OU`, `OU_LEVEL` | `import_gee`, `fetch_*`, `calc_orgUnit_alerts` | `OU_LEVEL`: Fokontany = 6, CSB = 5. |
| `DISEASE_CODE` | `fetch_disease`, `calc_orgUnit_alerts` | Code of the `pridec_historic_*` dataElement. |
| `ALERT_NAME`, `ALERT_FOCAL_DATE` | `calc_orgUnit_alerts` | `ALERT_FOCAL_DATE` is optional, defaults to current month. |
| `GEE_SERVICE_ACCOUNT`, `GEE_VARIABLES` | `import_gee` | `GEE_VARIABLES` is optional (all variables by default). Also needs `.gee-private-key.json`. |
| `PIVOT_URL`, `PIVOT_TOKEN` | `import_pivot_com`, `import_pivot_csb` | Pivot only. |

Individual environmental variables can also be provided to the docker image via the `--env` flag when running.

## Running tasks

The available tasks can be listed by running:

```
docker compose run etl --help
```

Each task also has its own help, which lists its specific options:

```
docker compose run --rm etl <task> --help
```

It is recommended to run tasks with the `--rm` flag to prevent orphaned containers.

# Task reference

## `import_gee` 

**Purpose:** Imports climate variables from Google Earth Engine (GEE) into the PRIDE-C instance.

**Workflow position:** Step 1, once per month. 

**Frequency:** 1x/month

**Reads:** GEE (via `.gee-private-key.json`), orgUnits under `PARENT_OU` from the instance, and a bundled rice-field geojson (used for `pridec_climate_floodedRice`).

**Writes:** Climate dataValues to the instance. Respects `DRYRUN`.

**Env vars:** Required: `DHIS_URL`, `DHIS_TOKEN`, `PARENT_OU`, `GEE_SERVICE_ACCOUNT`. Optional: `GEE_VARIABLES` (comma-separated; default all PRIDE-C variables).

**Arguments:** `--help` lists the available variables.

**Notes:** `floodedRice` is specific to Ifanadiana. Other regions need their own rice-field polygon. Orgunit level is hardcoded to 6 (Fokontany), so `OU_LEVEL` is ignored. Default imports the prior three months of data only. Typical runtime is 20-30 minutes for one health District when `floodedRice` is included, otherwise 5 minutes without `floodedRice`.

**Example:**
```
docker compose run --rm --env GEE_VARIABLES='pridec_climate_temperatureMean,pridec_climate_windspeed' etl import_gee
```

## `import_pivot_com`

**Purpose:** Imports community health site (COM) case counts for malaria, respiratory infection and diarrhea from the Pivot instance into the PRIDE-C instance as `pridec_historic_COMMalaria`, `pridec_historic_COMRespinf` and `pridec_historic_COMDiarrhea` (category option combo `pridec_COC_u5`).

**Workflow position:** Step 2, once per month, Pivot-only. 

**Frequency:** 1x/month

**Reads:** Pivot instance (`PIVOT_URL`) for health data.

**Writes:** Three dataElements to the PRIDE-C instance. Respects `DRYRUN`.

**Env vars:** Required: `DHIS_URL`, `DHIS_TOKEN`, `PIVOT_URL`, `PIVOT_TOKEN`.

**Notes:** Months with no reported value are set to 0 where the site reported total consultations, and dropped otherwise, to separate missing data from true zeros. The prior 8 months are imported and updated.

**Example:**
```
docker compose run --rm etl import_pivot_com
```


## `import_pivot_csb`

**Purpose:** Imports CSB case counts for malaria, respiratory infection and diarrhea from the Pivot instance into the PRIDE-C instance as `pridec_historic_CSBMalaria`, `pridec_historic_CSBRespinf` and `pridec_historic_CSBDiarrhea`.

**Workflow position:** Step 2, once per month, Pivot-only. 

**Frequency:** 1x/month

**Reads:** Pivot instance (`PIVOT_URL`) for health data.

**Writes:** Three dataElements to the PRIDE-C instance. Respects `DRYRUN`.

**Env vars:** Required: `DHIS_URL`, `DHIS_TOKEN`, `PIVOT_URL`, `PIVOT_TOKEN`.

**Example:**
```
docker compose run --rm etl import_pivot_csb
```

## `fetch_climate` 

**Purpose:** Downloads PRIDE-C climate data from the instance for forecasting.

**Workflow position:** Step 4, after analytics are built following monthly import. 

**Frequency:** 1x/`dataElement` run

**Reads:** Climate dataValues for orgUnits at `OU_LEVEL` under `PARENT_OU`. The last 8 years are requested. It queries `analytics`, and so requires the analytics tables to be rebuilt following import.

**Writes:** `input/climate_data.json` (`{"dataValues": [...]}`). The `input/` directory must already exist.

**Env vars:** Required: `DHIS_URL`, `DHIS_TOKEN`, `PARENT_OU`, `OU_LEVEL`.

**Example:**
```
docker compose run --rm etl fetch_climate
```

## `fetch_disease`

**Purpose:** Downloads historical disease data for one `dataElement` for forecasting.

**Workflow position:** Step 4, after analytics are built. Can be run in any order with other `fetch_*` tasks.

**Frequency:** 1x/`dataElement` run

**Reads:** The dataElement with code `DISEASE_CODE`, for orgUnits at `OU_LEVEL` under `PARENT_OU`. The last 6 years are requested.

**Writes:** `input/disease_data.json` (`{"dataValues": [...]}`). The `input/` directory must already exist. Any existing file is overwritten, so run the forecast for one disease before fetching the next.

**Env vars:** Required: `DHIS_URL`, `DHIS_TOKEN`, `PARENT_OU`, `OU_LEVEL`, `DISEASE_CODE`.

**Example:**
```
docker compose run --rm --env DISEASE_CODE='pridec_historic_CSBMalaria' etl fetch_disease
```

## `fetch_geojson`

**Purpose:** Downloads orgUnit polygons for the spatial part of the forecast.

**Workflow position:** Step 4. Can be run in any order with other `fetch_*` tasks.

**Frequency:** 1x/`dataElement` run

**Reads:** Polygons for orgUnits at `OU_LEVEL` under `PARENT_OU`.

**Writes:** `input/orgUnit_poly.geojson`. Unlike the other fetch tasks, it does not check that `input/` exists first. [TO DO]

**Env vars:** Required: `DHIS_URL`, `DHIS_TOKEN`, `PARENT_OU`, `OU_LEVEL`.

**Example:**
```
docker compose run --rm etl fetch_geojson
```

## `validate_inputs`

**Purpose:** Validates the files in `input/` before running the forecast.

**Workflow position:** Step 5, between the `fetch_*` tasks and the `forecast` service.

**Frequency:** 1x/`dataElement` run

**Reads (defaults, each overridable by an argument):**

| Argument | Default |
|----------|---------|
| `--config` | `input/config.json` |
| `--external_data` | `input/external_data.csv` (Optional) |
| `--disease_data` | `input/disease_data.json` |
| `--climate_data` | `input/climate_data.json` |
| `--orgunit_poly` | `input/orgUnit_poly.geojson` |

**Writes:** `input/config_valid.json`, `input/input_valid.json` and `input/polygon_valid.geojson`.

**Env vars:** None required beyond `LOG_LEVEL`.

**Notes:** `config.json` is not produced by any ETL task and must be provided by the user. The required keys are listed by `docker compose run --rm etl validate_inputs --help`.

**Example:**
```
docker compose run --rm etl validate_inputs --config input/my_config.json
```

## `calc_orgUnit_alerts`

**Purpose:** Estimates the number of orgUnits expected to see more cases than the average of the prior three years, and saves it as an alert dataElement payload to post.

**Workflow position:** Step 7, after `forecast` and before `post_forecast`.

**Frequency:** 1x/`dataElement` run

**Reads:** `input/disease_data.json`, `output/forecast.json`, and the instance at `DHIS_URL`.

**Writes:** `output/alerts.json`. It does not post anything. `post_forecast` posts the file if present.

**Env vars:** Required: `PARENT_OU`, `OU_LEVEL`, `DISEASE_CODE`, `ALERT_NAME`. Optional: `ALERT_FOCAL_DATE` (`YYYYMM`, default today). `DHIS_URL` and `DHIS_TOKEN` are passed to the calculation but not checked up front.

**Notes**: As calculations are done locally and nothing is written to a remote, `DRYRUN` does not impact this task.

**Example:**
```
docker compose run --rm --env ALERT_NAME='My alert' --env ALERT_FOCAL_DATE='202601' etl calc_orgUnit_alerts
```


## `post_forecast`

**Purpose:** Posts the forecast, and the alerts if present, to the PRIDE-C instance.

**Workflow position:** Step 8, after the model validation report has been checked.

**Frequency:** 1x/`dataElement` run

**Reads:** `output/forecast.json` (required: the task exits with an error if missing) and `output/alerts.json` (optional: a warning is logged if missing).

**Writes:** dataValues to the instance. Respects `DRYRUN`.

**Env vars:** Required: `DHIS_URL`, `DHIS_TOKEN`.

**Example:**
```
docker compose run --rm etl post_forecast
```

## `build_analytics`

**Purpose:** Triggers a rebuild of the analytics tables on the PRIDE-C instance. The PRIDE-C app reads data via `analytics`, so new data is not visible until the tables are rebuilt.

**Workflow position:** Steps 3 and 10: after importing data, and again after finishing all `dataElement` runs.

**Reads / writes:** No local files. Starts the analytics job on the instance.

**Env vars:** `DHIS_URL`, `DHIS_TOKEN`.

**Runtime:** 10-15 minutes on the Pivot instance. Larger instances will take longer.

**Notes:** The task only launches the job. Check the instance for the `completed` status before running dependent steps. [TO UPDATE]

**Example:**
```
docker compose run --rm etl build_analytics
```

## `update_key`

**Purpose:** Updates a key in the instance `dataStore` that tells the PRIDE-C app to clear users' local cache and re-download data.

**Workflow position:** Step 11. Run last, after all updates, including the final analytics rebuild.

**Reads / writes:** No local files. Writes one `dataStore` key. Respects `DRYRUN`.

**Env vars:** Required: `DHIS_URL`, `DHIS_TOKEN`.

**Example:**
```
docker compose run --rm etl update_key
```


# `forecast` (separate image)

The forecast is run by a separate docker image, [pridec_forecast](https://hub.docker.com/r/mvevans89/pridec_forecast). The `input` directory must contain the config and external data files. If their names differ from the defaults, supply them as arguments to `docker compose run`:

```
docker compose run --rm forecast --config "input/config.json"
```

Inspect the model validation report in `output/forecast_report.html`. If everything looks correct, continue with `post_forecast`.
