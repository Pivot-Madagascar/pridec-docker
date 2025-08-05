# Lab Notebook : PRIDE-C Forecast
## Michelle Evans (mevans@pivotworks.org)

## Useful things

`source .venv/bin/activate`: to start the python venv [only to use the data fetch]

## 2025-08-05

Today, I am working on the install script and the `post` service. The idea is the install script wlil make it an "app" that is available anywhere and so should be easier for us to do updates of multiple data streams.


The way it works is:

1. follow the automated install to have `pridec` available as a command line application
2. create a folder for the dataStream you want to forecast. It should contain `input/`, `output/`, and `.env`. In the `input/` folder should be the external_data.csv and the configurations for that dataStream/diesease. the .env should also include the correct `DISEASE_CODE`
3. Run the workflow via the following from within the dataStream folder:

```
#use etiher way to specify dataStream
pridec run --env-from-file .env --rm fetch
pridec run --env DISEASE_CODE="pridec_historic_CSBMalaria" --rm fetch

pridec run --rm forecast --config "input/config_malaria.json"

#PAY ATTENTION HERE AS THIS WILL CHANGE YOUR INSTANCE
pridec run --env DRYRUN=false --rm post 

pridec down --remove-orphans
```


## 2025-08-04

Met with Paul to plan some of this architecture. Probably the `fetch` and `post` steps will be handled by the ETL, and then the `forecast` will be within this docker container. Currently continuing to add the `fetch` step to this so we have one container that just works locally for now.

I was also thinking about how the `fetch` for disease data could be different for different instances. For example, our IRA data is the combination of multiple diagnoses/dataElements. Because this is kind of created seperately and then turned into pridec_historic_..., this is a seperate process and will just have to be part of what whoever manages that system will need to configure themselves.

### Docker code I was using before

```
docker build -t pridec-forecast -D --progress=plain . 2>&1 | tee build.log

docker run --volume "$(pwd)/input:/app/input:ro" \
  --volume "$(pwd)/output:/app/output:rw" \
  --rm  pridec-forecast \
  --config "input/test_config.json"
```

**TO DO:**
- ~~get `fetch` service working~~
- test in some seperate workflow to make sure the process works
- ~~write documentation and post to github. Update to be cleaner and just for the docker compose workflow. Move old notes to lab-notebook~~
- ~~somehow ensure the DISEASE_CODE in .env and config.json are the same. Easiest may be to not include it in config.json and just get it from the environmental variables or the disease data itself. [done, it is now based on the disease_data]~~
- add a script that "installs" the PRIDE-C software via a shell script to set the compose file path, then create a script to run this on multiple data sources. This is what I will have Toky run.

## 2025-08-03

I think I want to restructure to have one compose file that does all three services (fetch, forecast, post). This will make it easier to run the whole workflow and also can have simpler python-based containers for fetch and post. To do this, I created subdirectories for each service. Each subdirectory contains the Dockerfile needed for that service, following some instructions here: https://mariusniemet20.medium.com/containerize-your-multi-services-app-with-docker-compose-96c26c1fb8b6

I also want to adjust the location of the input and output directories to be higher up so they aren't nested probably? I've also added somethign so they are svaed by dataElement and date so they can be inspected and seperated from other forecasts. Then the post can just be provided the output directory to POST. Okay, actually I think this makes things more confusing so I will go back to just saving it within a folder. If someone wants to create their own "output" folder on a local machine then they can. This should keep the docker workflow from getting weird


## 2025-08-02

Adjusting my prototype docker to this actual workflow to see how it works. It works!! I added the code to run it to the `README.md`. I may have to think about what is the actual best way to set this up. Probably have a folder for each datastream, they can all use the same container/image, but then will have different input and output folders.

Question to ask Paul is whether it is better to just run the data fetching from within the docker container? probably not.

**TO DO:**
- make schematic of workflow (python fetch, docker container, output)
- create a Makefile that runs everything for one dataSource (fetching, docker, post output) [doing with docker compose now]

## 2025-08-01

Updated the PRIDE-C package. Checking everything still works. It does.

Finished a basic quarto doc as part of the workflow.

Tested using docker using a quick test on the Desktop. Seems to work fine, the only thing is the image build takes a very long time to install the INLA and PRIDE-C packages and the resulting image is quick big (5.8 GB).


**TO DO**:
- ~~create automated reports to check input data and predictions [just a little quarto doc]~~
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