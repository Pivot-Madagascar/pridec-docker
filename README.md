# PRIDE-C Docker

A docker container to run the PRIDE-C Forecast Workflow

## Installation

## Usage

This needs to be run in order( fetch > forecast).

The directories `input` and `output` must already exist. You will receive an error if that is not the case.

The `.env` file must be updated for your use case, or the ENV_VARIABLES provided directly to `docker compose run`.

0. Build the docker image

Build the docker image. This only needs to be done once.

```
docker compose build
docker compose build --no-cache #takes 15 minutes. assures it is clean
```

1. Run `fetch` service

This uses the ENV_VARIABLES stored in the `.env` file. It needs to be updated when using a different DHIS2 instance or dataSource following `.env.example`

```
docker compose --verbose run --rm fetch
```

Example providing ENV_VARIABLES directly:

TO DO

2. Run `forecast` service

For `forecast`, input must contain a `config.json` file and `external_data.csv` file. They can have other names, but must be in the `input` directory to work with compose. If their name is different, it needs to be supplied via an argument to `docker run`, as in the below example

```
docker compose --verbose run --rm forecast --config "input/test_config.json"
```

3. Clean up unused containers

```
docker compose down --remove-orphans
```

4. To run a service interactively

```
docker compose run --rm --entrypoint "/bin/bash" <service-name>
```

## Helpful testing code

**Never use `docker compose up` because it will run both services at once, and the `fetch` service must be run before the `forecast` service.** Eventualy I will write  a shell script that does this for all our data sources and will handle this automatically.

```
docker compose run --rm --entrypoint "/bin/bash" <service-name> #interactive shell

docker compose --verbose run <service-name>

docker compose logs -f <service-name>

docker image inspect <service-name>

docker run <service-name> --help

```

To rebuild full docker compose image from scratch (takes 15 minutes)

```
docker compose build --no-cache
```