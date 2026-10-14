# etlhub - Test Pipeline Michelle Log

This records incidents from testing the pipeline by hand. It also includes suggestions and notes.


### Data Import 

Everything seems to work fine for the Data Import.

Michelle will add an option for the DRYRUN to the python function behind the `Build Analytics` step. 

### Forecasts

1. It is slightly confusing to have the external_data upload before the button to open a run. I suggest adding it directly under the config.json section. For the PIVOT system, these could be automatically provided based on whether the data is ADJ/COM or CSB as a kind of default.

2. Add a default configuration for each dataElement and give the user an option to override by uploading a new one.

3. In the side window showing the steps, sometimes the `Data check` step will not be available to launch due to missing a config.json or external_data.json. Can we add make the upload of these files an explicit step so that it is clear to the user why the `Data check` step is not available?

4. The Forecast step encountered the following error when running full ensemble model that contained the INLA model:

```
── INLA Forecast 
Started: 2026-10-14 15:33:07
sh: 1: /usr/local/lib/R/site-library/INLA/bin/linux/64bit/inla.mkl.run: Permission denied
sh: 1: /usr/local/lib/R/site-library/INLA/bin/linux/64bit/inla.mkl.run: Permission denied
Error: INLA model failed with error message:
 The inla-program exited with an error. Unless you interupted it yourself, please rerun with verbose=TRUE and check the output carefully.
  If this does not help, please contact the developers at <help@r-inla.org>.
The inla program failed and the maximum number of tries has been reached.
Execution halted
```

I think this is an issue with the docker image, perhaps introduced by the `container_user`, because the package is installed as a root user. Michelle will investigate how to solve this. Continuing the test by removing the INLA model from the config by setting it to 0.

5. All of the output of the forecast pipeline is not showing in the logs. It showed when there was an error when I ran with the full model, but doesn't show when using a test config.json. When run natively via the docker image, this does output. It should look like:

```
✔ All input data files exist. Importing...
ℹ Using the following configurations:
$pred_vars
[1] "pridec_climate_temperatureMean" "pridec_climate_precipitation"  

$model_weights
   model weight
1   inla    0.0
2 glm_nb    0.0
3 ranger    0.5
4 arimax    0.0
5  naive    0.5

$quantile_levels
[1] 0.05 0.50 0.95

$forecast_start
[1] "202610"

$month_analysis
[1] 60

$month_assess
[1] 3

$inla_hyper
$inla_hyper$prec.unstruct
[1] 1e+00 5e-04

$inla_hyper$prec.spatial
[1] 1e+00 5e-04

$inla_hyper$prec.timerw1
[1] 1.00 0.01


$ranger_hyper
$ranger_hyper$mtry
NULL

$ranger_hyper$min.node.size
NULL

$ranger_hyper$num.trees
[1] 500


$month_lag
[1] 3

$disease_dataElement
[1] "pridec_historic_CSBMalaria"

Saving intermediate files and output in  output 
Directory will be created if it does not exist.
2026-10-14 17:48:54 : Processing and formatting input data
although coordinates are longitude/latitude, st_intersects assumes that they
are planar
2026-10-14 17:48:55 : Beginning forecast model
Forecast period: 2026-10-01 thru 2027-01-01

── PRIDE-C Forecast Workflow ──

Started: 2026-10-14 17:48:55

── RANGER Forecast 
Started: 2026-10-14 17:48:55

── Naive Forecast 
Started: 2026-10-14 17:48:56

── Creating stacked ensemble 
ℹ Finished ensemble stack. Time elapsed: 2 seconds.
2026-10-14 17:48:57 : Forecast model finished.
Saving intermediate files to output
✔ SUCCESS: Forecast created. Outputs saved in output/
ℹ Creating HTML report of forecast...
```


6. At the forecast approval step, give the user the option to download everything in the `output/`  and `input/` folder. This is sometimes needed to investigate an error in the data or forecasts before approval.

### Tracking

In the tracking page, requests that end in a 409 status do not show up with Details. Is this because they have been rerun? Could we add a word or something to signify that?

On this page, in addition to the API Status, can we add the log status. For eaxmple, an API can succeed with 202 but the actual task it launches may have an error. It would be helpful to have informatin on both. Or would it be better if the task returns an error to the API when it ends in an error? What is easiest for your system and what is the best practice?