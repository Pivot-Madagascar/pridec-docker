options(timeout = 3600)

remotes::install_bioc("graph")
remotes::install_bioc("Rgraphviz")
remotes::install_version("INLA", version = "25.06.07", repos = c(getOption("repos"), INLA = "https://inla.r-inla-download.org/R/stable"), dep = TRUE)
# INLA::inla.binary.install(os="Ubuntu-22.04") #to avoid matrix error messages
remotes::install_github("Pivot-Madagascar/PRIDEC-package", dependencies = TRUE)
