# runs the PRIDE-C forecasting model with validated inputs
parser <- optparse::OptionParser()
parser <- optparse::add_option(parser, c("--config_valid"), default = "input/config_valid.json",
                               type = "character",
                               help = "Path to json file containing validated model configurations for forecast.")
parser <- optparse::add_option(parser, c("--input_valid"), default = "input/input_valid.json",
                               type = "character",
                               help = "Path to validated input_data for forecasting step. Corresponds to input_data output by validate_inputs function/task.")
parser <- optparse::add_option(parser, c("--polygon_valid"), default = "input/polygon_valid.geojson",
                               type = "character",
                               help = "Path to validated polygons. Corresponds to graph_poly output by validate_inputs function/task.")
args <- optparse::parse_args(parser)


source("source_r/setup.R")

validate_args_exist(args = args)

config <- jsonlite::fromJSON(args$config_valid)
input_data <- jsonlite::fromJSON(args$input_valid)
graph_poly <- sf::st_read(args$polygon_valid, quiet = TRUE)

#format and save as list
input_data$period <- as.character(input_data$period)
required_columns <- c("orgUnit", "period", config$disease_dataElement, config$pred_vars)
#check variables are in the input_data
if(!(all(required_columns %in% colnames(input_data)))){
    missing_vars <- required_columns[!(required_columns %in% colnames(input_data))]
    stop(paste("Columns missing from input data:", paste(missing_vars, collapse = ", ")))
}
#graph_poly format
if(!("org_ID" %in% colnames(graph_poly))){
    stop("graph_poly is missing `org_ID` identifier")
}

input_list <- list(config = config,
                  input_data = input_data,
                  graph_poly = graph_poly)

cli::cli_alert_info("Using the following configurations:\n")
print(input_list$config)

forecast_status <- PRIDEC::run_pridec_forecast(inputs = input_list, output_dir = output_dir)

cli::cli_alert_success(paste0("SUCCESS: Forecast created. Outputs saved in ", output_dir, "/"))

cli::cli_alert_info("Creating HTML report of forecast...")
report_status <- PRIDEC::create_forecast_report(report_dir = output_dir, quiet = FALSE)

if(report_status){
    cli::cli_alert_success(paste0("SUCCESS: HTML report created at ", output_dir, "/forecast_report.html"))
} else {
    cli::cli_alert_warning(paste0("WARNING: Forecast created but report failed. Created simple report.",
                            "Investigate", output_dir, "/forecast.json and ", output_dir, "/input_data.RData.",
                            "Report can be re-run using `docker compose run forecast report-only`."))
}