# Default input files

> Since 2026-10-15. Code: `etlhub/infrastructure/default_files.py`, `InputUploadService` (`save_default`, `defaults`,
> `default_path`), `api/routers/input_router.py`. Tests: `etlhub/tests/api/test_default_files.py`.

A forecast run needs a `config.json` per disease and an `external_data.csv` per org unit level
(see [../pipeline-checkpoints/pipeline-checkpoints.md § 4.6](../pipeline-checkpoints/pipeline-checkpoints.md)). The user can upload their own files, or use the
**default file** etlhub offers for that item. A default is **offered, never applied automatically**: the user
clicks "Use default".

## Where the defaults come from

The defaults are files of the repository, under `assets/`, the **same in both modes** (since 2026-11-26):

| Item | Production and test mode |
|---|---|
| `config/Malaria` | `assets/forecast_configs/config_malaria.json` |
| `config/Diarrhea` | `assets/forecast_configs/config_diarrhea.json` |
| `config/Respinf` | `assets/forecast_configs/config_respiratory.json` |
| `external_data/fkt` (ADJ, COM) | `assets/forecast_configs/external_data_fkt.csv` |
| `external_data/csb` (CSB) | `assets/forecast_configs/external_data_csb.csv` |

The mapping is `SOURCES` in `default_files.py` (both keys point to one dict). `test_every_repo_default_exists` fails
if a file is renamed; `test_test_mode_offers_the_production_files` if the modes diverge again.

### Why test mode no longer has its own set (decision of 2026-11-26)

Until then test mode offered `assets/test/inputs/` (a CSB/Malaria set: `config.json` needing `mosquito_net`,
`external_data.csv` with 5 columns). Two problems:

- **Dates.** That set was built for the CLI's test mode, which forces `forecast_start` to `202601`; its
  `external_data.csv` covers `202101` to `202612`. etlhub sets `forecast_start` to the cycle, and the R forecast
  (`PRIDEC::split_cv_forecast`) needs the months `forecast_start - month_analysis` and
  `forecast_start + month_assess - 1` in the data. From the cycle `202611` on, every test-mode forecast with that
  default stopped in the container ("The data must contain the requested date range": needs `202701`, data until
  `202612`). Seen on 2026-11-25, while the same cycle passed in production with the production files
  (`201501` to `202712`).
- **Levels.** One file for every level: an ADJ/COM (fokontany) run failed at `validate_inputs` (no orgUnit in common).

Test mode is meant to rehearse production with the DHIS2 writes in dry run, so it now uses the production files.
Cost: INLA runs in test mode too (longer forecasts). `assets/test/inputs/` stays for the CLI test procedure
(`../../testing-QA/test-cli-cycle.md`) and the unit tests.

`validate_inputs` also refuses, since the same day, a grid that misses one of those two months
(`validation_use_cases._check_forecast_months`), whatever the mode and wherever the `external_data` comes from: the
job fails at validation with the months covered and the months needed, not minutes later in the forecast.

## Storage: none, the files of `assets/` as they are now

- etlhub reads the file of `SOURCES` on each request: no table, no seed. After a `git pull` that changes
  `config_malaria.json`, the new content is the default at once.
- **Limit**: no history of the defaults (`ponytail:` in the code). A table (metadata in `logs/etlhub.db`, content in
  `data/defaults/<hash>`) comes when admins can replace a default
  ([../pipeline-config/pipeline-config.md](../pipeline-config/pipeline-config.md), phase 4). Rule planned then: the most recent default wins,
  whether it comes from the repository or from an admin upload.
- **A missing file**: that item gets no default (no "Use default" button, uploads still work). Nothing is logged;
  `test_every_repo_default_exists` catches a renamed file of the repository.

## API

| Method & path | Does |
|---|---|
| `GET /input/defaults` | Defaults of the current mode: `{item: {filename, size}}`. A missing file is left out. |
| `GET /input/defaults/{config\|external_data}/{key}/preview?limit=100` | Same answer as `/input/files/*/preview`, for the default of `config/<key>` or `external_data/<key>`. 404 when there is none. |
| `POST /input/files/{config\|external_data}/from-default` | Copies the default of the **open run's** item into `input/`, through the same path as an upload: checks, `forecast_start` written into `config.json`, pipeline lock, checkpoint, `?confirm=true` rule (R5), copy kept in `uploads/<cycle>/`. 409 without an open run, 404 when the item has no default. |

## Interface (etlui)

Under each `FileDropzone` of a run's "Steps" dialog (`LevelColumn`: the run's `config.json` and `external_data.csv`, since 2026-10-16):
"Default · *filename* · *size*", with **Preview** (always available) and **Use default** (enabled only when the
upload is, i.e. a run of that disease or level is open). The server file shown after "Use default" is the same as
after an upload: nothing says it came from the default. The server file (**Preview**, **Delete**) is shown above the
dropzone, and the default is hidden while a server file exists: delete it to be offered the default again.

## Deployment

etlhub must reach `assets/` **in production too**. Paths are resolved from the repository root
(`Path(__file__).parents[2] / "assets"`), not from the working directory. There is no etlhub Dockerfile today; if
etlhub is containerized, mount `assets/` (read-only is enough).
