FROM rocker/geospatial:4.5.1

LABEL maintainer="pridec@pivotworks.org"
LABEL description="PRIDE-C Disease Forecasting Pipeline"

WORKDIR /app

COPY requirements.R .

RUN Rscript ./requirements.R

COPY scripts/ ./scripts/
COPY templates/ ./templates/
COPY entrypoint.R .

ENTRYPOINT ["Rscript", "/app/entrypoint.R"]