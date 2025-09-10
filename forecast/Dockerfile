FROM rocker/geospatial:4.5.1

LABEL maintainer="pridec@pivotworks.org"
LABEL description="PRIDE-C Disease Forecasting Pipeline"

WORKDIR /app

RUN curl -LO https://github.com/quarto-dev/quarto-cli/releases/download/v1.4.554/quarto-1.4.554-linux-amd64.deb
RUN sudo dpkg -i quarto-1.4.554-linux-amd64.deb
RUN rm quarto-1.4.554-linux-amd64.deb

COPY requirements.R .

RUN Rscript ./requirements.R

COPY scripts/ ./scripts/
COPY templates/ ./templates/
COPY entrypoint.R .

ENTRYPOINT ["Rscript", "/app/entrypoint.R"]