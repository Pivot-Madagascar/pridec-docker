# Lab Notebook : PRIDE-C Docker
## Michelle Evans (mevans@pivotworks.org)

## Useful things

`source .venv/bin/activate`: to start the python venv 

for testing on d2 docker-test: 
```
DHIS2_PRIDEC_URL="http://localhost:8082/"
DHIS2_TOKEN="d2pat_odhYW86O8auDuQ73u4r3HElEJxMFQziM3326734980"
```

Building and pushing to Docker Hub (both images at once)

```
docker compose -f compose-build.yaml build --no-cache && docker compose push
```

## 2026-04-22

Checking everything works brand new.

I am trying to streamline the pridec function, but there is a bit of confusion between docker compose arguments and arguments for the forecast entrypoint. I need some way to differentiate them. I figured it out. Basically now all teh arguments are provided after the service and/or command, but the only arguments that can give to docker compose are environmental variables. The rest are built in. If someone really wants to change them they can update the compose.yaml file

I am not going to worry about making github actions for these images. IT hink it makes the most sense to manually post them.

I've built the geolight base image so make the build faster. It should work exactly teh same and I am just updating where I pull from in the Dockerfile for `forecast`. It includes the PRIDE-C packages for now


**TO DO:**
- ~~build a geolight base image to save build time for forecast image (basically everything but the R script and pridec packages)~~

## 2026-04-21

Making some changes to how we use compose. There are now two compose files:

- `compose-build`: this builds the image locally. Needs to be done to update docker hub. Does not include volume mounts, so can only be used for building
- `compose`: this pulls the image from the Docker Hub or locally if it already exists. I have updated it to merge with `compose-auto` so that is can also use a provided argument of HOST_PWD. This means it is also used with the pridec call and allows for an installation without downloading all of the repo

The file needs to be specified anytime we use docker compose run, so  compose.yaml is the default. I have also updated the pridec "function" to use the correct compose file. I've also set the compose to create the directories on the host machine if they don't exist.

I also updated the `pridec` function to give more informative messages and the install.sh file to pull an image rather than building one.

It also now automatically takes the .env file from the current directory unless it is set seperately.

If you use an older version of docker compose, you may get a warning about no build being available. This is noise and can be ignored.

**TO DO:**
- build a geolight base image to save build time for forecast image (basically everything but the R script and pridec packages)

## 2026-04-17

Fixed the issues with the PRIDE-C package. Working on a lighter geospatial image.

Also fixed the `mbind: Operation not permitted` error which was due to specific capabilities in the docker. It is is solved by adding the `SYS_NICE` capability (https://man7.org/linux/man-pages/man7/capabilities.7.html) to help cores manage how they are being used.

I think for ease of use, I will keep using `docker compose` because there are so many things to specify that don't really change and it makes the one-liner commands much easier. What I can do though is put a compose file in each "sub-service" so that it is clear that they don't need to all be run at once. We may need to split the docker compose into each image, so that it gets attached to the images when they are uploaded to Docker Hub, but I'm not 100% sure.

**TO DO:**
- create github action to update docker image on PR to main branch. These could then be pulled directly by the ETL application.


## 2026-04-14

I did some reading and actually the best is probably to keep these in the same repo, but I can use paths to trigger the image builds and sending to Docker Hub automatically to do for just each one. This also lets us keep the compose workflow which is easier for doing everything locally. This also helps with variables being interpolated and more easily provided to the call via  `--env-file`, sine docker and docker compose deal with these differently.

**TO DO:**
- update forecasting report to do missing data on lagged data. Currently it does it on raw data so climate data is always missing [for PRIDE-C R package]
- ~~FULL RESET of data on PRIDE-C instance because there is something weird going on with teh sen2 indicators~~
- ~~add README.md documentation for each image~~
- use Github Actions for automated docker hub linkage

## 2026-03-24

I checked the Sen2 indicators and they seem fine. I think something just went wrong during an import during my maternity leave. My recommendation is to fully delete the historical climate and then re-import them.

I am adding a `README.md` file to each service of docker compose. This will hopefully then go to the dockerhub as a README.md. I can also create a github action so that when I push to main, it will push to the docker hub. For now, I have to do this manually which is kind of a pain.

Also, Paul had recommended a seperate image for each compose sub-service, and I think that does make the most sense to link it easiest with the Docker Hub. It does change the automated install and updates a bit though, so this is something for next month post-update. It will also require setting the binds within the Dockerfiles.

**TO DO:**
- update forecasting report to do missing data on lagged data. Currently it does it on raw data so climate data is always missing [for PRIDE-C R package]
- FULL RESET of data on PRIDE-C instance because there is something weird going on with teh sen2 indicators
- add README.md documentation for each image
- use Github Actions for automated docker hub linkage


## 2026-03-09

Doing the first production run of the new workflow. I'm doing this by hand so I can fix bugs as I go.

CSB - ~~all three finished~~
ADJ - ~~Mal~~, ~~Diar, Resp~~
COM - ~~Mal  Diar, Resp~~

An issue was with the Analytics table cache afterwards. Data is in DHIS2, but not available via analytics. So I think the whole table needs to be cleared via Maintenance before a new one is made. I have updated the `pivot_dhis_tools` `launch_analytics` function to do this now.


**TO DO:**
- ~~add default --rm flag to the pridec running so that there aren't orphaned containers [needs to be done in install.sh] [not possible]~~
- ~~update README with new workflow and ensure installation still works [just need to check the auto install]~~
- set up import_gee to only import certain variables based on the arguments, just to speed things up when needed or testing [added as issue]
- update forecasting report to do missing data on lagged data. Currently it does it on raw data so climate data is always missing [for PRIDE-C R package]
- FULL RESET of data on PRIDE-C instance because there is somethign weird going on with teh sen2 indicators

## 2026-03-06

I am going to finalize the docker image, then download the current PRIDE-C SQL dump and load it locally to do a full test.

Things for full test (ensure pridec-202603 d2 container is up):
```
docker compose build etl --no-cache #to install
docker compose run --rm etl --help
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl import_pivot_com
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl import_pivot_csb
docker compose run --env-from-file .env --env DRYRUN="true" --rm etl import_gee
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl fetch_climate
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl fetch_disease
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl fetch_geojson
docker compose run --rm forecast
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl post_forecast
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl calc_CSB_alerts
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl update_key
docker compose run --env-from-file .env --env DRYRUN="false" --rm etl build_analytics
```
Everything worked!

Testing the forecast
```
docker compose build forecast --no-cache #to install
docker compose run --rm forecast
```

Okay so an issue is that the CSB's are just points and not their actual catchment. So I think to think of a way to do this. Probably easiest is to provide the data via the pivot_dhis_tools package and then source that when the OU_LEVEL is something in particular. This will be very Pivot specific but I think is okay for now. I ended up just adding a catch for this in teh pridec_gee package

**TO DO**:
- ~~remove other images~~
- ~~add csb vigilance~~
- ~~add update dataStore~~
- add default --rm flag to the pridec running so that there aren't orphaned containers [needs to be done in install.sh]
- update README with new workflow and ensure installation still works
- set up import_gee to only import certain variables based on the arguments, just to speed things up when needed or testing

## 2026-03-05

The python scripts are mostly done for the `etl` module. They have been tested and most come from the `pivot_dhis_tools` or `pride_gee` package.

I'm also adding some housekeeping scripts for internal use. Actually i will do this later, but at lesat the one to delete would be very useful.

So to test out the etl microservice (ensure DHIS_URL is set to a d2 local instance)

```
docker compose build etl --no-cache #to install
docker compose run --rm etl --help
docker compose run --env-from-file .env --env DRYRUN="true" --rm etl fetch_geojson

```

I have tested every argument and they all work. The other images can be removed and then this used to update PRIDE-C for this month.

**TO DO**:
- ~~finish individual scripts~~
- ~~write docker file for ETL bit~~
- remove other images
- ~~write bash CLI dispatcher~~
- ~~add check to config to make sure all the variables exist~~: doing this by function
- update documentation by specifying types in functions themselves to get better error messages (this is to do in the packages)
- add default --rm flag to the pridec running so that there aren't orphaned containers [needs to be done in install.sh]
- update README with new workflor and ensure installation still works


## 2026-03-04

Working on a simple re-org for now with a bash CLI dispatcher. Can always update later when I have the time to deal with python module hierarchies.

I spent way too long messing with how env variables are provided. I am having issues with updating them via the CLI. But I think I will just move everything over and then deal with that later. I think the issue is the config.py file? But I have the LOG_LEVEL inthere and it seems to be working fine. The fix was the order things were called in. Configs need to be called before anythign else apparently

- ~~import_pivot_COMcases~~
- ~~import_pivot_CSBcases~~
- ~~OR import_pivot to do all~~ [later]
- ~~import_gee~~
- ~~analytics~~
- ~~fetch_input_climate ~~: written in `pivot_dhis_tools`, need to move over here.
- ~~fetch_input_disease~~
- ~~fetch_input_geojson~~
- OR fetch_inputs to get all (mayeb provide an argument do select some?)
- forecast [seperate image]
- ~~post forecasts~~

**TO DO**:
- finish scripts above
- write docker file for ETL bit
- remove other images
- write bash CLI dispatcher

## 2026-03-03

I was working on combining all the API stuff into a nice "package' but it ended up getting way too complicated to connect everything. So I think I will just use a bash-based CLI dispatcher to run the appropriate scripts and I can use folders to organize them a bit. Any 'arguments' will just be provided via the `.env` file or the environment via the `-e` in docker. Otherwise I am building out for too much flexibility and it is taking too long. I will still use the `config.py` to store all the environmental variables though. And then different "tasks" will be provided via an argument that will be dispatched via bash. I can look at how it works in teh pivot update to see how logs and things will be managed. The import_pivot_COM that is there is a good example.

## 2026-03-02

The `forecast` code is working fine. It is now structured to be almost entirely contained in the PRIDE-C package, plus one small file in the docker service.

The API python requests will be in a service. Ok, because I don't actually need multiple thigns runnign simutaneously, I think I could just do one image that takes in deifferent calls and then has a python dispatcher file that calls the appropriate python script. The scripts I would need are:

- import_pivot_COMcases
- import_pivot_CSBcases
- OR import_pivot to do all
- import_gee
- analytics
- fetch_input_climate
- fetch_input_disease
- fetch_input_geojson
- OR fetch_inputs to get all (mayeb provide an argument do select some?)
- forecast [seperate image]
- post forecasts

There are functions in the utils files that could be moved to the pivot_dhis_tools package to call on

## 2027-02-27

Testing the new code from the PRIDE-C package in teh docker image to be sure it works okay.

**TO DO:**
- update pridec_gee code
- combine everything python based into one microservice/image

## 2026-02-26

Updating teh forecast microservice to take functions directly from PRIDE-C package. Very little of the actual code is now stored in this docker image.

**TO DO:**
- combine fetch, import and post services into one docker microservice with different entrypoints so as to not duplicate docker images. All can use python 3.12.
- move pivot-specific api commands into `pivot_dhis_tools` python package and just call it for import pivot data. Same for fetch and post scripts.

## 2026-02-18

I've moved much of the forecasting code into functions in the PRIDE-C package, this can then be updated in the docker forecast microservice.

**TO DO**:
 - INLA is returning odd `mbind: Operation not permitted` error. Not sure where it is coming from. Probably from messed up installation? I can redo the `inla.binary.install()` to fix this. This is an error on the docker image.

## 2026-02-10

I think best is to start with the seperate package structures and then make the changes in those. We have three packages that everything fits into:

1. PRIDE-C R Package: this contains everything needed for data validation and forecasting. It will also contain some functions for getting data from DHIS2 for those data scientists that want to work only in R
2. pridec-gee Python package: this is a package that contains all of the functions for getting data from GEE for PRIDE-C, or any other project that needs climate. IT can be fed the orgUnits and dates/frequency we want data for and then returns it in a way that is formatted to be sent to a dhis2 instance, although the POSTing will have to be done seperately
3. pivot-dhis2-utils Python package: this is an internal package that contains some utility functions that we use for working with DHIS2 data because currently those functions are spread all over. Some of this could also be used by others, but we are not developing it with that in mind. This includes moving/updating PIVOT data, getting data from Pivot DHIS2, DELETING historical data when needed, etc. A lot of this functionality is in the old R package and just needs to be rewritten into python real quick.

I will slowly start moving this over from this docker repo as we adjust our workflow.

## 2026-02-09

As I go through the PRIDE-C update with "new eyes", here is a list of things to update:

**GEE**
- drop emojis, looks like it is vibe coded. Maybe just keep X for an error. Much of this is in GEE package. add line spaces to messages
- add something to signal time when teh flood data import starts because it takes so long. Also option to run in background?
- add ability to only import certain environmental variables based on arguments provided. This is especially useful because the flood data takes ages
- add some kind of status check for the GEE step, to see where the flood data is at
- add month option to import for when we need to import super old
- something is going on with climate data not updating and showing up as missing in the forecasts (not sure why)
- mndwi is having an error starting July 2025 and starts flipping to totally different numbers

**PRIDEC**
- INLA is returning odd `mbind: Operation not permitted` error. Not sure where it is coming from.
- forecast report doesn't open in Firefox, only chrome
- move several of the forecasting steps (like data validation) to the PRIDE-C package so it can be updated most easily
- add something to debug when the data seems off. Could just be something that points to the data to inspect from teh forecast_html?, like with code to read it in in R or python?
- print more information messages on errors

**pivot-dhis2-utils**
- seperate out Pivot-specific things into a `pivot-dhis2-utils` python package. I think we can do a similar thing with any of the python scripts for PRIDE-C, and then we just need to load that package with the plumber app so that it is updated each time
- when running Analytics table, ping back when it is finished (look in `"level": "LOOP"`)
- update fetch in forecast step to only get those we need
- save POST responses somewhere so that debugging is easier (like a log)
- import community cases for all fokontany and do the filtering of predictions on the back-side [import-pivot-data/COMcases.py]


As we move the application to plumber, some of this will be easier to implement on that side


## 2025-08-12

Working on service that imports data from Pivot instance. I'll develop it in a seperate folder and the move it over once it is all working. This is based on some existing code I have that is a mix of R and python, but I will migrate it all to Python.

Also through doing this I think using the tag for the post is a little confusing, so I will just change it to python entrypoint where the name of the script needs to be provided. especially since they are really doing two seperate things. Realistically everything that works with the API (fetch, post, import-pivot-data, analytics) could be run through one service and then the script that is run is changed? Eh, leave them seperate for now, the python images are so small it doesn't make a huge difference I don't think.

Added the data import step as a service.

**TO DO:**
- add option for saving intermediate model outputs (or just always do it just in case)
- update data checking/cleaning to be dependent on data source (this is kind of specific to us, but fine for now)
- update `pridec-pivot-update` workflow for new import services

## 2025-08-11

Working on adding the GEE importation workflow as a service to this. I will also add the Pivot Health data importation as a service, so that everything is here in one place.

I also added a way to update analytics via the `post` service so that can be run after everything is finished.

**TO DO:**
- add pivot specific data update workflow to docker (we just won't expose it)
- add option for saving intermediate model outputs (or just always do it just in case)
- update data checking/cleaning to be dependent on data source (this is kind of specific to us, but fine for now)

## 2025-08-08

Trying to use the `pridec-pivot-update` in production today. I first tested on CSBMalaria and got some super crazy predictions for one orgUnit. My guess is its due to the ARIMAX model being difficult, so I changed the weight from 0.57 to 0. that did solve the problem tbf, so I removed ARIMAX for all of the predictions for now. this also makes it much much faster.

It also could be helpful to be able to provide a flag that saves the intermediate model objects for trouble-shooting/investigating this type of thing.

**TO DO:**
- add option for saving intermediate model outputs (or just always do it just in case)
- update data checking/cleaning to be dependent on data source (this is kind of specific to us, but fine for now)

## 2025-08-07

workign on debuggin the issue with the geojson. The issue was that the polygons on the instance are very old and not valid by newer spatial norms, this was fixed via `sf::st_make_valid()`.

Also checked on CSB, ADJ, and COM data and it seems to work.


**TO DO:**
- ~~investigate fokontany geojson error with ADJ data. This may also have to do with how we don't use all the fokontany for the COM predictions~~
- finish writing documentation and go through a full "clean" run

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

#PAY ATTENTION HERE AS THIS WILL CHANGE YOUR INSTANCE. update DRYRUN as needed
pridec run --env-from-file .env --env DRYRUN=true --rm post

pridec down --remove-orphans
```

**Testing on other dataStreams**

I started testing on other dataStreams. When using the COMDiarrhea, I seem to be getting values at CSB levels in addition to fokontany. I think this is an error in fetch_disease_input.py. OO or it may becuase the external_data is at the CSB level and needs to be provided at the fokontnay level. I will see if that fixes it. It did.

I also spun it up on a local d2 instance to test it and it seems to work. When testing something on a local d2 instance, we have to linkt he local host. I updated the compose files to include `network_mode; "host"` to deal with this.

I also created a new repo that contains the workflow specific to Pivot (`pridec-pivot-update`). This would be what another sysadmin would use to base their own thing own. 

I am getting a weird error with the polygons for the fokontany data, so I need to look into this and see what is going on.

**TO DO:**
- investigate fokontany geojson error with ADJ data. This may also have to do with how we don't use all teh fokontany for the COM predictions
- finish writing documentation and go through a full "clean" run

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