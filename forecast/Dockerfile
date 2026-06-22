FROM mvevans89/geolight:latest

WORKDIR /app

COPY cli_r.sh .
RUN chmod +x cli_r.sh
COPY 01_validate-inputs.R .
COPY 02_forecast.R .
COPY 03_create-report.R .
COPY source_r ./source_r

ENTRYPOINT ["./cli_r.sh"]