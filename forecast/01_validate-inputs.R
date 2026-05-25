#validates the input data. will print many messages, but will run without error if input is valid
source("source_r/setup.R")

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

validate_args_exist(args = args)

config <- jsonlite::fromJSON(args$config)
external_data <- read.csv(args$external_data)
disease_data <- jsonlite::fromJSON(args$disease_data)
climate_data <- jsonlite::fromJSON(args$climate_data)
orgUnit_poly <- sf::st_read(args$orgUnit_poly, quiet = TRUE)

cli::cli_h2(paste(round(Sys.time()), ": Importing and validating inputs"))

valid_check <- PRIDEC::validate_inputs(config = config,
                                       external_data = external_data,
                                       disease_data = disease_data,
                                       climate_data = climate_data,
                                       orgUnit_poly = orgUnit_poly)

if(!valid_check){
  stop("Invalid inputs. Halting forecast.")
} else {
    results <- PRIDEC::validate_inputs(config = config,
                                       external_data = external_data,
                                       disease_data = disease_data,
                                       climate_data = climate_data,
                                       orgUnit_poly = orgUnit_poly,
                                       return_inputs = TRUE)
    #save to be read in by the forecast task (can update this as needed by FastAPI)
    jsonlite::write_json(results$config, "input/config_valid.json", pretty = TRUE, auto_unbox = TRUE, null = "null")
    jsonlite::write_json(results$input_data, "input/input_valid_.json", pretty = TRUE, auto_unbox = TRUE, null = "null")
    sf::st_write(results$graph_poly, "input/polygon_valid.geojson", delete_dsn = TRUE)
    print("Validated config saved to input/config_valid.json")
    print("Validated input data saved to input/input_valid.json")
    print("Validated orgUnit polygons saved to input/polygon_valid.geojson.")
}