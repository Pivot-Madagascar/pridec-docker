# Use specific R version for reproducibility
FROM rocker/geospatial:4.5.1

# Set maintainer
LABEL maintainer="pridec@pivotworks.org"
LABEL description="PRIDE-C Disease Forecasting Pipeline"

# Create app directory
WORKDIR /app

# Copy R package requirements file
COPY requirements.R .

# Install R packages with specific versions
RUN Rscript ./requirements.R

# Copy R scripts and templates
COPY scripts/ ./scripts/
COPY templates/ ./templates/
COPY entrypoint.R .

# Set entrypoint
ENTRYPOINT ["Rscript", "/app/entrypoint.R"]