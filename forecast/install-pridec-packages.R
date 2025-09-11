options(timeout = 3600)

remotes::install_bioc("graph")
remotes::install_bioc("Rgraphviz")
remotes::install_version("INLA", version = "25.06.07", repos = c(getOption("repos"), INLA = "https://inla.r-inla-download.org/R/stable"), dep = TRUE)
remotes::install_github("Pivot-Madagascar/PRIDEC-package", dependencies = TRUE)
