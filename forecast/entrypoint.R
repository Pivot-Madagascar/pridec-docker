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
  
  library(PRIDEC)
  
  library(dplyr)

})


validate_args_exist <- function(args){
  err_count <- 0
  for(i in 2:length(args)){ #2 to skip help
    if(!file.exists(args[[i]])){
      cli::cli_alert_danger(paste0("File not found for argument `", names(args)[[i]], "` : ",
                  args[[i]]))
      err_count <- err_count+1
    }
  }
  if(err_count>0){
    cli::cli_abort("Input data missing. Please verify filepaths.")
  } else {
    cli::cli_alert_success("All input data files exist. Importing...")
  }
}



# Start ##############################################

cli::cli_h1(paste(round(Sys.time()),": Running PRIDE-C Forecast Pipeline"))


# Validate Input Files #################################

cli::cli_h2(paste(round(Sys.time()), ": Importing and validating inputs"))

validate_args_exist(args = args)

config <- jsonlite::fromJSON(args$config)
external_data <- read.csv(args$external_data)
disease_data <- jsonlite::fromJSON(args$disease_data)
climate_data <- jsonlite::fromJSON(args$climate_data)
orgUnit_poly <- sf::st_read(args$orgUnit_poly, quiet = TRUE)

valid_check <- PRIDEC::validate_inputs(config = config,
                                  external_data = external_data,
                                  disease_data = disease_data,
                                  climate_data = climate_data,
                                  orgUnit_poly = orgUnit_poly)

if(!valid_check){
  stop("Invalid inputs. Halting forecast.")
}


input_list <- PRIDEC::validate_inputs(config = config,
                                  external_data = external_data,
                                  disease_data = disease_data,
                                  climate_data = climate_data,
                                  orgUnit_poly = orgUnit_poly,
                                  return_inputs = TRUE)

cli::cli_alert_info(c("Using the following arguments:\n",
                      "External data:", args$external_data, "\n",
                      "Configurations:"
))
print(input_list$config)

# Run Forecast #################################
                        
output_dir <- "output"

forecast_status <- PRIDEC::run_pridec_forecast(inputs = input_list, output_dir = output_dir)

#return messages based on status and create a report
if(forecast_status){
    cli::cli_alert_success("SUCCESS: Forecast created.")
    cli::cli_alert_info("Creating HTML report of forecast...")
    report_status <- PRIDEC::create_forecast_report(report_dir = output_dir, quiet = FALSE)

    if(report_status){

      cli::cli_alert_success(paste0("SUCCESS: HTML report created at ", output_dir, "forecast_report.html"))
      
    } else {

      cli::cli_alert_warning(paste0("WARNING: Forecast created but report failed. Created simple report.",
                              "Investigate", output_dir, "forecast.json and ", output_dir, "input_data.RData.",
                              "Report can be re-run using `Rscript -e 'PRIDEC::create_forecast_report()'."))
    }

  }