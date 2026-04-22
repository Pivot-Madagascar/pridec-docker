# PRIDE-C ETL Docker Image

This docker image is used to run the PRIDE-C Forecast step.

# Usage

## Building Service

The service should be built using `docker compose` v2. This will pull the image from the docker Hub, rather than building it locally.

```
curl -o compose.yaml https://raw.githubusercontent.com/Pivot-Madagascar/pridec-docker/refs/heads/main/compose.yaml
docker compose build forecast
```

You can also build the service locally from the github repo, downloaded via `git`. To build the service locally run:

```
git clone https://github.com/Pivot-Madagascar/pridec-docker.git
cd pridec-docker
docker compose build forecast
```

Note that the directory structure below must be added to the `pridec-docker` folder to run if it is built this way.

## Directory Structure

The image requires the following directory structure within the project directory:

```
──  input/
│   ├──  climate_data.json
│   ├──  config.json
│   ├──  disease_data.json
│   ├──  external_data.csv
│   └──  orgUnit_poly.geojson
├──  output/
```

The `climate_data.json`, `disease_data.json`, and `orgUnit_poly.geojson` can be imported using the [pridec_etl docker image](https://hub.docker.com/r/mvevans89/pridec_etl). 

The `external_data.csv` is optional, but must include the columns `period` (in YYYYMM format) and `orgUnit`, corresponding to the orgUnit `UID`s you wish to forecast.

The `config.json` file contains model configurations for the forecast model. It follows the following template:

```
{
   "pred_vars": ["predvar1", "predvar2"],
    "model_weights": [
        {
            "model" : "inla",
            "weight": 0.36
        },
                {
            "model" : "glm_nb",
            "weight": 0.0
        },
                {
            "model" : "ranger",
            "weight": 0.39
        },
                {
            "model" : "arimax",
            "weight": 0
        },
                {
            "model" : "naive",
            "weight": 0.12
        }
    ],
    "quantile_levels" : [0.05, 0.5, 0.95],
    "forecast_start" : "YYYYMM",
    "month_analysis" : 60,
    "month_assess" : 3
}
```

Forecast outputs will be saved in the `output` directory. This includes the forecasts themselves and a forecast report HTML document.

### forecast command

The forecast can be run using the following command:

```
docker compose run --rm forecast
```

There are internal checks for the validity of input data and model processes. The output of these will be printed to the console. If the input data is not valid, it will need to updated and the command re-run.

After the forecast has finished, you can inspect `output/forecast_report.html` to validate the input data and forecasts. PRIDE-C forecasts can be posted to a DHIS2 instance via the [`pridec_etl` docker image](https://hub.docker.com/r/mvevans89/pridec_etl).