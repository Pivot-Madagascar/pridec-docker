FROM rocker/geospatial:4.5.1

LABEL maintainer="pridec@pivotworks.org"
LABEL description="PRIDE-C Disease Forecasting Pipeline"

RUN sudo apt update

WORKDIR /app

#quarto comes with rocker image, shouldn't need to install seperately
RUN sudo apt install jq -y

# install R packages line by line to help with cache
RUN R -e "install.packages('remotes')"

# RUN R -e "remotes::install_bioc('graph')"
# RUN R -e "remotes::install_bioc('Rgraphviz')"
# RUN R -e "remotes::install_version('INLA', version = '25.06.07', repos = c(getOption('repos'), INLA = 'https://inla.r-inla-download.org/R/stable'), dep = TRUE)"
# RUN R -e "remotes::install_github('Pivot-Madagascar/PRIDEC-package', dependencies = TRUE)"

COPY install-pridec-packages.R .
RUN Rscript ./install-pridec-packages.R


RUN Rscript -e "remotes::install_version('optparse', version = '1.7.5', repos = 'http://cran.us.r-project.org')"
RUN Rscript -e "remotes::install_version('cli', version = '3.6.5', repos = 'http://cran.us.r-project.org')"
RUN Rscript -e "remotes::install_version('skimr', version = '2.1.5', repos = 'http://cran.us.r-project.org')"
RUN Rscript -e "remotes::install_version('paletteer', version = '1.6.0', repos = 'http://cran.us.r-project.org')"
RUN Rscript -e "remotes::install_version('here', version = '1.0.1', repos = 'http://cran.us.r-project.org')"
RUN Rscript -e "remotes::install_version('jsonlite', version = '2.0.0', repos = 'http://cran.us.r-project.org')"
RUN Rscript -e "remotes::install_version('quarto', version = '1.5.1', repos = 'http://cran.us.r-project.org')"


COPY scripts/ ./scripts/
COPY templates/ ./templates/
COPY entrypoint.R .

ENTRYPOINT ["Rscript", "/app/entrypoint.R"]