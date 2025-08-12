# PRIDE-C Docker

A docker container to run the PRIDE-C Forecast Workflow

## Requirements

- [docker compose](https://docs.docker.com/compose/install/)
- 6 GB storage space for docker image
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

### Install via `install.sh` (recommended, Mac/Linux only)

This shell script will install the PRIDE-C Docker app and make it available via the command `pridec`. This will allow you to access the pridec services from anywhere using `pridec` instead of `docker compose`.

change the `COMPOSE_DIR` variable in `pridec` to the path to `pridec-docker`. your `pridec` file should look like this:

```
#!/bin/bash

COMPOSE_DIR="/path/to/pridec-docker" #update to be path to installed repo
HOST_PWD="$(pwd)"
HOST_PWD="$HOST_PWD" docker compose -f "$COMPOSE_DIR/compose-auto.yaml" "$@"
```

Run the install script. This will take 15-20 minutes depending on your internet connection.:

```

chmod +x install.sh
./install.sh
```

Check it is installed correctly:

```
pridec config
which pridec
```

### Use `docker compose build` directly (manual install)

You can also use the application directly via `docker compose`. This will take about 15 minutes the first time it is run.

```
docker compose build
docker compose build --no-cache #takes 15 minutes. ensures it is clean
```

To use `pridec`, it must be run from within the `pridec-docker` directory. This is best used for one off runs, and not full automated workflows where multiple dataElements are predicted. This follows the Manual Install usage below.

## Usage (auto install)

An example of an automated workflow using a shell script is available in the [pridec-pivot-update repo](https://github.com/Pivot-Madagascar/pridec-pivot-update/tree/main).

The primary steps are:

1. Create a project directory for the dataElement you wish to predict
2. Create `input` and `output` subdirectories
3. Copy your `config.json` and `external_data.csv` into the `input` directory. See example files [here](https://github.com/Pivot-Madagascar/pridec-pivot-update/tree/main/forecast_assets).
4. Create a `.env` file with the following variables at project directory:

```
DHIS2_PRIDEC_URL="your-url" 
DHIS2_TOKEN="your-token"
PARENT_OU="VtP4BdCeXIo" #id of parent orgUnit. Ifanadiana: "VtP4BdCeXIo"
DISEASE_CODE="pridec_historic_yourDataElement" #corresponds to DHIS2 dataElement code of disease to predict
GEE_PROJECT = "YOUR_GEE_PROJECT_NAME"
GEE_SERVICE_ACCOUNT="YOUR_SERVICE_ACCOUNT@YOUR_CLOUD_PROJECT.iam.gserviceaccount.com"
#the below is only needed for Pivot-specific workflows to update DHIS2 data
PIVOT_URL="pivot-production-url"
PIVOT_TOKEN="your-token-for-pivot-instance"
```

5. Run the full workflow from the project directory. Some example code is below:

```
#import data from google early engine into your DHIS2 instance (this only needs to be done once per month)
pridec run --env-from-file .env --env DRYRUN="true" --rm import-gee

#import data from Pivot instance (this is specific to Ifanadiana), run once per month
pridec run --env-from-file .env --env DRYRUN=true --rm import-pivot-data COMcases.py
pridec run --env-from-file .env --env DRYRUN=true --rm import-pivot-data CSBcases.py

#run analytics table before fetching
pridec run --env-from-file .env --env DRYRUN=true --rm post analytics.py

pridec run --env-from-file .env --rm fetch
#allows you to keept same URL and TOKEN and just change DISEASE_CODE
pridec run --env-from-file .env --env DISEASE_CODE="pridec_historic_CSBMalaria" --rm fetch

#config file can be changed for each disease
pridec run --rm forecast --config "input/config_malaria.json"

#YOU SHOULD INSPECT output/forecast_report.html NOW

#PAY ATTENTION HERE AS THIS WILL CHANGE YOUR INSTANCE. update DRYRUN as needed
pridec run --env-from-file .env --env DRYRUN=true --rm post post.py

#to run analytics table
pridec run --env-from-file .env --env DRYRUN=true --rm post analytics.py


pridec down --remove-orphans
```

## Usage (manual install)

If it is manually installed, these steps need to be run from the `pridec-docker` project directory.

This needs to be run in order (import > fetch > forecast > post).

The directories `input` and `output` must already exist in the `pridec-docker` directory. You will receive an error if that is not the case.

The `.env` file must be updated for your use case, or the ENV_VARIABLES provided directly to `docker compose run`.

### 1. `import-gee` service to import GEE climate varables into DHIS2 instance [once per month]

This requires having a `.gee-private-key.json` in the root directory as well as a `GEE_SERVICE_ACCOUNT` in `.env`. There is one climate variable that is specific to Ifanadiana (`pridec_climate_floodedRice`) and that will eventually need updating to make more generalizable.

```
docker compose run --env-from-file .env --env DRYRUN=false --rm import-gee
```

In order for this data to be available via `analytics` calls, the Analytics Tables must be rebuilt:

```
docker compose run --env-from-file .env --env DRYRUN=true --rm post analytics.py
```

### 2.  `import-pivot-data` service to import Madagascar specific data (Pivot-only) [once per month]

This is an optional service to only be run on the Pivot PRIDE-C instance. It creates the `pridec_historical_` variables that are needed for predictions. This is needed because there is some cleaning and formatting we do with the raw `dataElements` to have high quality variables to predict.

```
docker compose run --env-from-file .env --env DRYRUN=true --rm import-pivot-data COMcases.py
docker compose run --env-from-file .env --env DRYRUN=true --rm import-pivot-data CSBcases.py
#analytics tables should be rebuilt after this
docker compose run --env-from-file .env --env DRYRUN=true --rm post analytics.py
```

### 3. `fetch` service to download climate, disease, and geospatial data

This uses the ENV_VARIABLES stored in the `.env` file. It needs to be updated when using a different DHIS2 instance or dataSource following `.env.example`. This step is run for every `dataElement` that you wish to predict.

```
docker compose run --rm fetch
```

Example providing ENV_VARIABLES directly:

```
docker compose run --env DISEASE_CODE="pridec_historic_CSBMalaria" --rm fetch
```

### 4. `forecast` service to create predictions.

For `forecast`, input must contain a `config.json` file and `external_data.csv` file. They can have other names, but must be in the `input` directory to work with compose. If their name is different, it needs to be supplied via an argument to `docker run`, as in the below example

```
docker compose run --rm forecast --config "input/config.json"
```

You should now inspect the model validation report in `output/forecast_report.html`. If everything seems okay, proceed to step 3 to import the forecast into the PRIDE-C instance.

### 5. Run `post` service

By default, this is always a dry run (makes no changes to an instance). This is to serve as a kind of double-check to ensure production data is only changed purposefully.

```
docker compose run --env DRYRUN=true --rm post post.py
docker compose run --env DRYRUN=true --rm post analytics.py #launch export of analytics table
```


### 6. Clean up unused containers (optional)

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