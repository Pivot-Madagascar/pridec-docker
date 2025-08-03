#Utility functions for PRIDE-C Docker workflow

#' Validate Input Files
#' Check that input files exist and if not return a stop
#' @param args list of arguments provided via CLI
#' @returns Nothing, but verifies if input data is valid and exists.
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
    cli::cli_alert_success("All input data files exist.")
  }
}

#' Function to load and validate input data
#' @param args list of arguments provided via CLI
#' @returns list containing model configurations, input data, and sf polygon object to be used to create INLA graph 
load_validate_inputs <- function(args){
  err_count <- 0
  
  ## Config #######################
  config <- jsonlite::fromJSON(args$config)
  
  #weight for each model
  missing_modelWeight <- c("inla", "glm_nb" ,"ranger", "arimax", "naive")[which(!(any((c("inla", "glm_nb" ,"ranger", "arimax", "naive") %in% config$model_weights$model))))]
  if(length(missing_modelWeight)>0){
    cli::cli_alert_danger(c("The following model weights are missing from the {.code config.json} file:",
                            missing_modelWeight))
    err_count <- err_count + 1
  }
  
  #add check for period format, quantile levels (3 of them, numeric), month_analysis and month_asses(postivie integer)
  
  
  ## External Data ################
  #ensure it includes orgUnit and period
  external_data <- read.csv(args$external_data)
  if(any(!(c("orgUnit", "period") %in% colnames(external_data)))){
    cli::cli_alert_danger("External data must include columns {.code orgUnit} and {.code period}.")
    err_count <- err_count + 1
  }
  
  external_data <- external_data[,which(colnames(external_data) %in% 
                                          c("orgUnit", "period", config$pred_vars))]
  external_data$period <- as.character(external_data$period)
  

  
  ## Climate Data #################
  
  climate_data <- jsonlite::fromJSON(args$climate_data)$dataValues
  climate_data$period <- as.character(climate_data$period)
  
  ## Disease Data ################
  
  disease_data <- jsonlite::fromJSON(args$disease_data)$dataValues
  disease_data$period <- as.character(disease_data$period)
  #drop any extra columns we don't want
  disease_data <- disease_data[,c("orgUnit", "period", "dataElement", "value")]
  #require at least 3 years of data to model
  disease_data <- disease_data |>
    dplyr::mutate(n_months = sum(!is.na(value)),
           .by = "orgUnit") |>
      dplyr::filter(n_months>=36) |>
      dplyr::select(-n_months)
  
  ## Combine into one dataframe to use ###########
    
    #first date - assessment
    min_date <- as.Date(paste0(min(disease_data$period), "01"), format = "%Y%m%d") - lubridate::period(month = config$month_assess)
  
  input_data <- dplyr::bind_rows(disease_data, climate_data) |>
    tidyr::pivot_wider(names_from = "dataElement", values_from = "value") |>
    dplyr::full_join(external_data, by = c("orgUnit", "period")) |>
    dplyr::filter(as.Date(paste0(period, "01"), format = "%Y%m%d") >= min_date)
  
  ## Check all the predictor variables are there ################
  
  missing_predVars <- config$pred_vars[which(!(config$pred_vars %in% colnames(input_data)))]
  if(length(missing_predVars)>0){
    cli::cli_alert_danger(c("The following predictor vairables are missing from the input data:\n",
                            missing_predVars))
    err_count <- err_count + 1
  }
  
  if(!(config$disease_dataElement %in% colnames(input_data))){
    cli::cli_alert_danger(c("{.code disease_dataElement} misspecified in {.code config.json}.\n",
                            paste0("Current value: ", config$disease_dataElement)))
    err_count <- err_count + 1
  }
  
  ## geojson polygons ########################
  
  graph_poly <- sf::st_read(args$orgUnit_poly, quiet = TRUE)
  graph_poly$org_ID <- 1:nrow(graph_poly)
  
  #check every orgunit has a polygon
  all_ou <- unique(input_data$orgUnit)
  missing_orgPoly <-all_ou[which(!(all_ou %in% graph_poly$orgUnit))]
  if(length(missing_orgPoly)>0){
    cli::cli_alert_danger(c("The following orgUnits are missing corresponding polygons in `OrgUnit_poly`:\n",
                            missing_orgPoly))
    err_count <- err_count + 1
  }
  
  #Return error or input data
  if(err_count>0){
    cli::cli_abort("Error importing inputs. See notes above.")
  } else {
    cli::cli_alert_success("Succesfully imported inputs.")
    return(list(config = config,
                input_data = input_data,
                graph_poly = graph_poly))
  }
}

#' Format predictor variables for ensemble_forecast
#' @param var_list string vector of predictor variables
#' @param input_data data.frame of input data
format_pred_vars <- function(var_list, input_data){
  dynamic_vars <- c("pridec_climate_precipitation", "pridec_climate_temperatureMean", 
                    "pridec_climate_relHumidity", "pridec_climate_evi", "pridec_climate_mndwi", 
                    "pridec_climate_gao", "pridec_climate_propFire", "pridec_climate_AOD", 
                    "pridec_climate_windspeed", "pridec_climate_floodedRice")
  
  #lag the climate variables
  vars_to_lag <- var_list[var_list %in% dynamic_vars]
  #scale the numeric variables
  vars_to_scale <- colnames(Filter(is.numeric, input_data[,var_list]))
  
  #update names to match predictor variables after prep
  pred_vars <- var_list
  pred_vars[which(var_list %in% vars_to_lag)] <- paste0(pred_vars[which(var_list %in% vars_to_lag)], "_lag")
  pred_vars[which(var_list %in% vars_to_scale)] <- paste0(pred_vars[which(var_list %in% vars_to_scale)], "sc")

  return(list(pred_vars = pred_vars,
              vars_to_lag = vars_to_lag,
              vars_to_scale = vars_to_scale))
}

#' Format forecasts to be posted to DHIS2 instance
#' @param forecast_out data.frame output of `ensemble_forecast`
#' @param disease_dataElement dhis2 code that represents the dataElemtn to be forecast
#' @param forecast_start date of forecast start in `date` format. Must be first day of month (YYYY-MM-01).
#' @returns cleaned formatted data.frame for DHIS2
format_forecast_dhis2 <- function(forecast_out, disease_dataElement, forecast_start){
  forecast_out |>
    dplyr::filter(dataset == "assess") |>
    dplyr::filter(date < (forecast_start + months(3)),
           date > forecast_start - months(48)) |>
    dplyr::mutate(predicted = as.integer(round(predicted)),
           period = paste0(substr(date,1,4), substr(date,6,7))) |>
    dplyr::mutate(dataElement = dplyr::case_when(
      quantile_level < 0.5 ~ paste0(gsub("historic", "forecast", disease_dataElement), "LowCI"),
      quantile_level == 0.5  ~ paste0(gsub("historic", "forecast", disease_dataElement), "Avg"),
      quantile_level > 0.5~ paste0(gsub("historic", "forecast", disease_dataElement), "UppCI"),
    )) |>
    dplyr::mutate(categoryOptionCombo = "pridec_COC_u5") |>
    dplyr::select(orgUnit, period, value = predicted, dataElement, categoryOptionCombo) |>
    dplyr::distinct()
  
  
}

#' Validate formatted data for DHIS2
#' @params formatted DHIS2 forecast
#' @returns prints number of NA, non-integer, and negative values. These should all be zero
check_dhis_value <- function(this_df){
  this_value <- pull(this_df, value)
  err_1 <- sum(is.na(this_value))
  print(paste("numNA:", err_1))
  err_2 <- sum(!is.integer(this_value))
  print(paste("non-integers:", err_2))
  err_3 <- sum(this_value<0, na.rm = TRUE)
  print(paste("negative values:", err_3))
  
  if(sum(err_1,err_2,err_3)>0) {
    cli::cli_abort("Forecast contains non-real or negative numbers. Inspect `ensemble_forecast` outputs.")
  }
  
}

#' Create Forecast Report
#' Creates a forecast report using quarto
#' @param config_file path to configuration file for this model. Default = "input/config.json"
#' @param doc_title Title of report. Default = "PRIDE-C Forecast Report"
#' @param output_dir Directory for output for docker runs
#' @returns Creates a HTML report of forecast at output/forecast_report.html
create_forecast_report <- function(config_file = "input/config.json",
                                   doc_title = "PRIDE-C Forecast Report",
                                   output_dir){
  
  #move template to output to run
  file.copy("templates/validation_report_template.qmd", to = "tmp_template.qmd",
            overwrite = TRUE)
  
  quarto::quarto_render(
    input = "tmp_template.qmd",
    output_file = "tmp_quarto-out.html",
    execute_params = list(config_json = config_file),
    quarto_args = c("--metadata", paste0("title=", doc_title))
  )
  
  #move and clean up files
  file.copy("tmp_quarto-out.html", to = paste0(output_dir, "forecast_report.html"),
            overwrite = TRUE)
  file.remove("tmp_template.qmd")
  file.remove("tmp_quarto-out.html")
  
}
