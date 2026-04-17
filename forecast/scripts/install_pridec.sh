#!/bin/bash
set -e

## build ARGs
NCPUS=${NCPUS:--1}

#graph, Rgraphviz, INLA, PRIDEC
Rscript /rocker_scripts/install-pridec-packages.R 

install2.r --error --skipinstalled -n "$NCPUS" \
    optparse \
    skimr \
    paletteer \
    here \
    jsonlite \
    quarto

# Clean up
rm -rf /var/lib/apt/lists/*
rm -rf /tmp/downloaded_packages

## Strip binary installed lybraries from RSPM
## https://github.com/rocker-org/rocker-versioned2/issues/340
strip /usr/local/lib/R/site-library/*/libs/*.so