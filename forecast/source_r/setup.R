
# Load Packages ##########################
suppressPackageStartupMessages({
  library(jsonlite)
  library(cli)
  library(optparse)
  library(sf)
  
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

#set output direcoty (this can be changed later or provided via a parameter if we want)
output_dir <- "output"