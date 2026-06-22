# creates 

source("source_r/setup.R")

cli::cli_alert_info("Creating HTML report of forecast...")
report_status <- PRIDEC::create_forecast_report(report_dir = output_dir, quiet = FALSE)

if(report_status){
    cli::cli_alert_success(paste0("SUCCESS: HTML report created at ", output_dir, "/forecast_report.html"))
} else {
    cli::cli_alert_warning(paste0("WARNING: Forecast created but report failed. Created simple report.",
                            "Investigate", output_dir, "/forecast.json and ", output_dir, "/input_data.RData.",
                            "Report can be re-run using `Rscript -e 'PRIDEC::create_forecast_report()'."))
}