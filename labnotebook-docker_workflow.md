# Lab Notebook : PRIDE-C Forecast
## Michelle Evans (mevans@pivotworks.org)

## Useful things

`source .venv/bin/activate`: to start the python venv [only to use the data fetch]



## 2025-08-01

Updated the PRIDE-C package. Checking everything still works. It does.

Finished a basic quarto doc as part of the workflow.

Tested using docker using a quick test on the Desktop. Seems to work fine, the only thing is the image build takes a very long time to install the INLA and PRIDE-C packages and the resulting image is quick big (5.8 GB).



**TO DO**:
- create automated reports to check input data and predictions [just a little quarto doc]
- ~~update to new PRIDEC package to make sure it fixes ARIMA issue~~ 
- figure out how this works with Docker (use a dumb example that only uses a naive model to test). probably needs INLA image

## 2025-07-30

Working on how to get the data from PRIDE-C via some python scripts. This will be what Paul will implement via the ETL, and also adds easy tracking to ensure we remember where our sandbox data comes from.

Finished for the climate data.

Need to update for `geojson` data and `disease` data. but should follow a similar format. [Done]. Added note to README.md in input folder to explain how to update this data.

**TO DO**:
- ~~check that entrypoint.R works as it should and also maybe saves things somewhere?~~
- create automated reports to check input data and predictions [just a little quarto doc]
- update to new PRIDEC package to make sure it fixes ARIMA issue
- figure out how this works with Docker (use a dumb example that only uses a naive model to test). probably needs INLA image

## 2025-07-24

Working on throwing it all in a Docker. I think if I want to use a pipeline, I will use Nextflow because it is better for me to learn. But probably jsut writing it up in Docker is enough as there are not so many steps.

I need to create a "testing json" of CSB-level data. Although maybe I can just get that automatically from our DHIS2 instance. Done.

Currently in the process of porting over the individual steps of the `run_ensemble_forecast` into the `entrypoint.R` script so that the data cleaning and prep is a little more isolated and easier to track for when errors arise. The `config.json` now takes all of the parameters needed to run that.

Teh data goes into the `input` folder. Probably we can write an ETL that automatically updates this. It should mostly all be pulled from a DHIS2 instance, although external data can also be provided. For our case, the external data is unchanging.

**TO DO:**
- check that entrypoint.R works as it should and also maybe saves things somwhere?
- create automated reports to check input data and predictions
- update to new PRIDEC package to make sure it fixes ARIMA issue
- figure out how this works with Docker (use a dumb example that only uses a naive model to test). probably needs INLA image


## 2025-07-23

Started a seperate project so I can develop a more general PRIDE-C forecast workflow that will eventually be run inside a Docker container that will the one shared with others. It needs to not include things specific to Pivot, as the `pridec-forecast-workflow` repo does right now. It also only reproduces the forecasting step. Because this step is mostly contained within a package, this should result in a Snakemake file that is not horrible long.

I will start by testing with one dataset (malaria at the CSB level) because this is the easiest.

I will run it using a local DHIS2 server for now, to reduce download times.  What needs to be provided?

- ~~url for DHIS2~~
- ~~DHIS2 token to access the instance~~: I think rather htan accessing the instance, this will be provided 
- external data to be used [add a check to ensure it is complete] (csv or path to it?)
    - must include orgUnit and period columns, rest can be whatever
    - or this can always be put in the same place in the Docker container and saved as external_data or something so we don't have an issue
- list of variables to include [will need to add a check to ensure this is in data]
    - from this list can get the individual climate variables from instance (better to this each time rahter than download all?)
- name of dataElement to predict (use code)
- model weights (eventaully also tuning configs?)

What is output?
- html report to allow for checking of input data and predictions
- json file of predictions to upload to DHIS2