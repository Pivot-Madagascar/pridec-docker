# Lab Notebook : PRIDE-C Forecast
## Michelle Evans (mevans@pivotworks.org)

## Useful things

`source .venv/bin/activate`: to start the python venv

## 

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