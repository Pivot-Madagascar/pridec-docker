options(timeout = 3600)

#install remotes 2.5.0 first
install.packages("remotes")

# Define package versions for reproducibility
packages <- c(
  "jsonlite@1.8.7",
  "optparse@1.7.5",
  "cli@3.6.5",
  "skimr@2.1.5",
  "paletteer@1.6.0",
  "here@1.0.1"
)

# Install packages with specific versions
for (pkg in packages) {
  pkg_parts <- strsplit(pkg, "@")[[1]]
  pkg_name <- pkg_parts[1]
  pkg_version <- if(length(pkg_parts) > 1) pkg_parts[2] else NULL
  
  if (!is.null(pkg_version)) {
    # Install specific version
    remotes::install_version(pkg_name, version = pkg_version, 
                             repos = "http://cran.us.r-project.org")
  } else {
    # Install latest version
    install.packages(pkg_name, repos = "http://cran.us.r-project.org")
  }
}

#install packages from elsewhere if needed
remotes::install_bioc("graph")
remotes::install_bioc("Rgraphviz")
remotes::install_version("INLA", version = "25.06.07", repos = c(getOption("repos"), INLA = "https://inla.r-inla-download.org/R/stable"), dep = TRUE)
remotes::install_github("Pivot-Madagascar/PRIDEC-package", dependencies = TRUE)
