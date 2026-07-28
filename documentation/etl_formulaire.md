# ETL Hub Configurations
**Updated July 28 2026**

The PRIDE-C ETL Hub is responsible for the following primary workflows:
- **Import**: Updating data on the PRIDE-C DHIS2 instance with new GEE and pivot data
- **Forecast**: Creating forecasts for any number of specified dataElements and posting this data to the PRIDE-C Instance
- **Update**: Update the dataStore Key so that the PRIDE-C application updates

Configurations are supplied via environmental variables to the docker image and task being run.

All images and tasks have documentation that can be accessed via the `--h` or `-help` flags.

All workflows require the `DHIS_URL` and `DHIS_TOKEN` envVars to be provided in order to access the DHIS2 instance. This authorization can also be handled internally when the ETL Hub is installed on an instance.

## IMPORT

Frequency: 1x per month. It is recommended to do this step the day before the **FORECAST** step so that imported data can be integrated into Analytics tables during the nightly build. This workflow would be run via cron job or by the system administrator.

Configurations for this workflow would be set at the instance-level by the admin and not by the user.

### docker compose run etl import_gee

Imports environmental data from Google Earth Engine into DHIS2 instance.

**`GEE_SERVICE_ACCOUNT`: service account information associated with the gee key.** 

Example: <your-account>@<your-project>.iam.gserviceaccount.com'

Requires a `.gee-private-key.json` (this may be possible to source from DHIS2 instance itself in future, see [here](https://docs.dhis2.org/en/manage/reference/google-service-account-configuration.html))

Instructions for creating these authorization variables can be found [here](https://developers.google.com/earth-engine/guides/service_account).


**`GEE_VARIABLES`: string of variables to import**

Run the following to see the available variables: `docker compose run --rm etl import_gee --help`. Defaults to all.

Example Usage: `docker compose run --env GEE_VARIABLES='pridec_climate_temperatureMean,pridec_climate_windspeed' etl import_gee`

**`PARENT_OU`: ID of parent orgUnit under which to import variables**

For Ifanadiana, this is `VtP4BdCeXIo`

### docker compose run etl import_pivot_com

This is a Pivot-specific task that is used to transfer community case data from Pivot's DHIS2 instance to the PRIDE-C DHIS2 instance.

**`PIVOT_URL`: url of PIVOT DHIS2 instance**

This is currently: https://www.dhis2-pivot.org/prod/

**`PIVOT_TOKEN`: personal access token associated with PIVOT DHIS2 instance**

### docker compose run etl import_pivot_csb

This is a Pivot-specific task that is used to transfer CSB case data from Pivot's DHIS2 instance to the PRIDE-C DHIS2 instance.

**`PIVOT_URL`: url of PIVOT DHIS2 instance**

This is currently: https://www.dhis2-pivot.org/prod/

**`PIVOT_TOKEN`: personal access token associated with PIVOT DHIS2 instance**

### docker compose run build_analytics 

This is only necessary if the **FORECAST** step is being run immediately after the **IMPORT** step, otherwise the tables will be built following the instance's schedule. This only requires the `DHIS_URL` and `DHIS_TOKEN`.

## FORECAST

This step is run for every `dataElement` that you would like to forecast. For the PIVOT PRIDE-C instance, it must be run nine times.

### Configurations/Formulaire

**Environmental Variables**
- `DISEASE_CODE`: The code of the dataElement you wish to forecast. Follows the format `pridec_historic_<source><disease>`. Example: `pridec_historic_CSBMalaria`. As a function of this code, the disease, data source, `ALERT_NAME` and `OU_LEVEL` can be set.
- `PARENT_OU`: ID of parent organization for which to create forecasts. Ifandaiana = `VtP4BdCeXIo`
- `OU_LEVEL`: orgUnit level at which to forecast the dataElement and estimate the number of orgUnits on alert. Set as a function of `DISEASE_CODE` source. When source is ADJ or COM, OU_LEVEL= 6. When source is CSB, OU_LEVEL = 5. This should eventaully be set by a dict that is stored in dataStore.
- `ALERT_NAME`: name of the orgUnit alert. On PIVOT's instance, this is set as a function of the `DISEASE_CODE` following the format `<source><disease>Vigilance`
- `dryRun`: whether to run the forecast in a test mode. Options: TRUE/FALSE

**User-provided Files**
- `input/config.json`: A configuration file for the forecast model to be run. Defaults for each `DISEASE_CODE` are stored in the `assets` folder. For more info run `docker compose run etl validate_inputs --h`.
- `input/external_data.csv`: An optional csv of additional predictor variables not stored in the DHIS2 instance, often socio-demographic or programmatic in nature. Defaults for each `DISEASE_CODE` are stored in the `assets` folder. For more info run `docker compose run etl validate_inputs --h`.


### subtasks

**Fetch Inputs**
`docker compose run etl fetch_disease`
`docker compose run etl fetch_climate`
`docker compose run etl fetch_geojson`

**Validate Inputs**
`docker compose run etl validate_inputs`

**Forecast**
`docker compose run forecast forecast`
`docker compose run etl calc_orgUnit_alerts`

**Post Forecast**
`docker compose run etl post_forecast`

## UPDATE

Once all of the forecasts have been posted, the application key can be updated so that the user's PRIDE-C app cache is reset. Optionally, the Analytics Tables can also be built, if this will not be done on a set schedule.

This does not require any additional configurations.

`docker compose run etl build_analytics`
`docker compose run etl update_key`






## Notes

Documentation for all tasks exists via the command line and can be accessed via the `--h` or `-help` flags:

```
docker compose run etl --help
docker compuse run forecast --help
```