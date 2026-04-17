FROM docker.io/library/ubuntu:noble

ENV R_VERSION="4.5.2"
ENV R_HOME="/usr/local/lib/R"
ENV TZ="Etc/UTC"

COPY scripts/install_R_source.sh /rocker_scripts/install_R_source.sh
RUN bash /rocker_scripts/install_R_source.sh

ENV CRAN="https://p3m.dev/cran/__linux__/noble/2026-03-10"
ENV LANG=en_US.UTF-8

COPY scripts/setup_R.sh /rocker_scripts/setup_R.sh
RUN bash /rocker_scripts/setup_R.sh

#copy all scripts first to help with making executable
COPY scripts/ /rocker_scripts/
#update permissions on all .sh so they are executable
RUN chmod -R +x /rocker_scripts/

RUN /rocker_scripts/install_base_packages.sh
RUN /rocker_scripts/install_pandoc.sh
RUN /rocker_scripts/install_quarto.sh
RUN /rocker_scripts/install_geospatial.sh

RUN /rocker_scripts/install_pridec.sh

WORKDIR /app

COPY entrypoint.R .

ENTRYPOINT ["Rscript", "/app/entrypoint.R"]