# entrypoint.R - Main orchestration script for the forecasting pipeline 

#' to run:
#' Rscript entrypoint.R --config "input/config.json" --external_data "input/external_data.csv"
#' 
#' to see arguments:
#' Rscript entrypoint.R --help

# parse command line arguments provided to docker container (may need to update paths to include app)
parser <- optparse::OptionParser()
parser <- optparse::add_option(parser, c("--external_data"), default = "input/external_data.csv",
                               type = "character", 
                               help="Path to external data in CSV format. Must include columns `orgUnit` and `period`.")
parser <- optparse::add_option(parser, c("--climate_data"), default = "input/climate_data.json",
                               type = "character",
                               help = "Path to json file containing PRIDE-C climate data from DHIS2.")
parser <- optparse::add_option(parser, c("--disease_data"), default = "input/disease_data.json",
                               type = "character",
                               help = "Path to json file containing data for the dataElement you want to predict.")
parser <- optparse::add_option(parser, c("--orgUnit_poly"), default = "input/orgUnit_poly.geojson",
                               type = "character",
                               help = "Path to geojson file containing polygons of the orgUnit catchments to use in INLA model.")
parser <- optparse::add_option(parser, c("--config"), default = "input/config.json",
                               type = "character",
                               help = "Path to json file containing model configurations for forecast.
                               See `templates/config_ex.json` for an example.")
args <- optparse::parse_args(parser)

# Load Packages ##########################
suppressPackageStartupMessages({
  library(jsonlite)
  library(cli)
  library(optparse)
  
  library(tidyr)
  library(qs2)
  
  library(PRIDEC)
  
  library(dplyr)

})


source("scripts/utils.R")

#set output dir
output_dir <- "output/"

# Start ##############################################

cli::cli_h1(paste(round(Sys.time()),": Running PRIDE-C Forecast Pipeline"))
cli::cli_alert_info(c("Using the following arguments:\n",
                          "External data:", args$external_data, "\n",
                          "Configurations:"
                      ))
print(fromJSON(args$config))

# Validate Input Files #################################

cli::cli_h2(paste(round(Sys.time()), ": Importing and validating inputs"))

validate_args_exist(args = args)
inputs <- load_validate_inputs(args = args)


# Clean and Process Data ##############################

cli::cli_h1(paste(round(Sys.time()), ": Processing and formatting data"))


## turn forecast start to date --------------------
#turn into function?
if(is.null(inputs$config$forecast_start)){
  #set to first date of this month
  forecast_start <- lubridate::rollback(Sys.Date(), roll_to_first = TRUE)
} else {
  forecast_start <- as.Date(paste0(inputs$config$forecast_start,"01"), format = "%Y%m%d")
}

## create list of dynamic and lagged variables ------------
variables <- format_pred_vars(var_list = inputs$config$pred_vars,
                             input_data = inputs$input_data)

## Prepare Data -----------------------------------------

data_prep_list <- PRIDEC::prep_data(raw_data = inputs$input_data,
                                    y_var = inputs$config$disease_dataElement,
                                    lagged_vars = variables$vars_to_lag,
                                    scaled_vars = variables$vars_to_scale,
                                    lag_n = 3,
                                    graph_poly = inputs$graph_poly)

forecast_cv <- PRIDEC::split_cv_forecast(data_to_split = data_prep_list$data_prep,
                                         forecast_start_date = forecast_start,
                                         month_analysis = inputs$config$month_analysis,
                                         month_assess = inputs$config$month_assess)




# Run Forecasting Model -----------------------------
cli::cli_h1(paste(round(Sys.time()),": Running forecast model"))
cli::cli_alert_info(paste("Forecast period:", forecast_start, "thru", forecast_start + lubridate::period(month = inputs$config$month_assess)))

## Model Configs -----------------------------------

#move this to formatting input function
model_weights <- inputs$config$model_weights$weight
names(model_weights) <-  inputs$config$model_weights$model

model_configs <- list()
model_configs$inla<- list(reff_var = NULL, pred_vars = variables$pred_vars,
                          hyper_priors = list("prec.unstruct" = c(1, 5e-4),
                                              "prec.spatial" = c(1, 5e-4),
                                              "prec.timerw1" = c(1,0.01)),
                          W_orgUnit = data_prep_list$W_graph, 
                          sample_pi = TRUE,
                          weight = model_weights["inla"])
model_configs$glm_nb <- list(pred_vars = variables$pred_vars,
                             weight = model_weights["glm_nb"])
model_configs$ranger <- list(pred_vars = variables$pred_vars,
                             hyper_control = list("mtry" = NULL, "min.node.size" = NULL, "num.trees" = 500),
                             weight = model_weights["ranger"])
model_configs$arimax <- list(pred_vars = variables$pred_vars,
                             log_trans = TRUE,
                             weight = model_weights["arimax"])
model_configs$naive <- list(group_vars = c("month_season", "orgUnit"),
                            weight = model_weights["naive"])

#if any weight is 0, do not fit that model
zero_weights <- names(model_weights)[which(model_weights==0)]
model_configs[names(model_configs) %in% zero_weights] <- NULL

# Run ensemble ------------------------------------------------------#

stack_forecast <- PRIDEC::ensemble_forecast(cv_set = forecast_cv,
                                            y_var = inputs$config$disease_dataElement,
                                            id_vars = c("orgUnit", "date"),
                                            quantile_levels = inputs$config$quantile_levels,
                                            inla_configs = model_configs$inla,
                                            glm_nb_configs = model_configs$glm_nb,
                                            ranger_configs = model_configs$ranger,
                                            arimax_configs = model_configs$arimax,
                                            naive_configs = model_configs$naive,
                                            return_individual_models = FALSE)


# Save Forecast Data ---------------#
#' can also save a file of metadata if you want (or provide this in report)
#' 

dhis2_forecast <- format_forecast_dhis2(forecast_out = stack_forecast, 
                                        disease_dataElement = inputs$config$disease_dataElement,
                                        forecast_start = forecast_start)

forecast_json <- toJSON(list("dataValues" = dhis2_forecast))
write(forecast_json, paste0(output_dir,"forecast.json"))

# Generate HTML Report from Results --------------------------------#
#' this will be saved in outputs
#' inspects input data and outputs

#save input data to investigate
qs2::qs_save(forecast_cv, paste0(output_dir, "input_data.qs"))
sf::st_write(inputs$graph_poly, paste0(output_dir, "polygon.gpkg"), append = FALSE,
             quiet = TRUE)

suppressMessages({
  create_forecast_report(config_file = args$config,
                         output_dir = output_dir)
})


cli::cli_alert_success(paste0(round(Sys.time()), " : Created forecast report at ", output_dir, "forecast_report.html"))
