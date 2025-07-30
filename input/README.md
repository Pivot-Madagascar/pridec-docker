# Input data

This folder contains the data that should be input to the docker applicatioon to create the PRIDE-C forecasts. All of this data comes from a DHIS2 instance in the full workflow, but is saved locally for development purposes.

A backup version of this data is saved in `base`.

Python scripts are used to FETCH the climate, disease, and geojson data. Configuration and external data are provided manually.

You should have a `.env` file in teh root directory with the following structure:

```
DHIS2_PRIDEC_URL="YOUR URL"
TOKEN_DHIS_PRIDEC_MICHELLE="YOUR ACCESS TOKEN"
PARENT_OU="VtP4BdCeXIo" #corresponds to Ifanadiana
OU_LEVEL="5" #6=fokontany, 5 = CSB
DISEASE_CODE="pridec_historic_CSBMalaria" #code of DHIS2 data element you want to predict
```

To fetch all the input data at once, run the following:

```
source .venv/bin/activate
python python-fetch-scripts/fetch_climate_input.py 
python python-fetch-scripts/fetch_disease_input.py 
python python-fetch-scripts/fetch_geojson_input.py 
```



## `climate_data.json`

This includes all of the PRIDE-C climate data variables for the past ten years (or as long as is available if less). It is fetched via `python-fetch-scripts/fetch_climate_input.py` and saved in `input/climate_data.json`.

```
source .venv/bin/activate
python python-fetch-scripts/fetch_climate_input.py 
```

The saved `json` file uses the following structure:

```
"dataValues": [
        {
            "orgUnit": "ZPvH8UsgwYv",
            "period": "201501",
            "dataElement": "pridec_climate_precipitation",
            "value": 21.4679
        },
        {
            "orgUnit": "ZPvH8UsgwYv",
            "period": "201501",
            "dataElement": "pridec_climate_temperatureMean",
            "value": 22.3457
        },
        ...
]

```

## `config.json`

This is the json config file that contains the configuratoin for the modeling workflow. It could be created via GUI or uploaded manually by the user. It should have the following format:

```
{
    "pred_vars": ["pridec_climate_temperatureMean", "pridec_climate_precipitation"],
    "disease_dataElement": "pridec_historic_CSBMalaria",
    "model_weights": [
        {
            "model" : "inla",
            "weight": 0
        },
                {
            "model" : "glm_nb",
            "weight": 0
        },
                {
            "model" : "ranger",
            "weight": 0
        },
                {
            "model" : "arimax",
            "weight": 0
        },
                {
            "model" : "naive",
            "weight": 0.3
        }
    ],
    "quantile_levels" : [0.05, 0.5, 0.95],
    "forecast_start" : "202504",
    "month_analysis" : 60,
    "month_assess" : 3
}
```

## `disease_data.json`

This corresponds to the historical disease data from DHIS2 that will be used to train the model to predict. It is fetched via `python-fetch-scripts/fetch_disease_input.py` and saved in `input/disease_data.json`. Which dataElement is downloaded depends on the `DISEASE_CODE` environmental variable in `.env`. To fetch the data run:

```
source .venv/bin/activate
python python-fetch-scripts/fetch_disease_input.py 
```

## `external_data.json`

Optional data to be provided that can not be stored following the DHIS2 structure. It requires columns `orgUnit` and `period` that match those from DHIS2. It would be provided by the user (uploaded via the GUI). For now, it is just stored locally.


## `orgUnit_poly.geojson`

The geojson corresponding to the orgUnit associated with the dataSource. It is fetched via `python-fetch-scripts/fetch_geojson_input.py`.

```
source .venv/bin/activate
python python-fetch-scripts/fetch_geojson_input.py 
```