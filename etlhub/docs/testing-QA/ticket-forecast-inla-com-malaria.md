# Forecast COM/Malaria fails in the INLA model: "Matrix is not (numerical) positive definite"

## Summary

The forecast step of the COM/Malaria run (dry-run cycle `202504`) fails every time INLA has a non-zero weight. It has failed 4 times on 2026-10-21. No file is written to `output/`.

The error persists with **complete covariates and the production Malaria config** (`forecast_22ee563a`). So the input data is ruled out as the only cause, and the INLA binary or the INLA call in the PRIDEC package becomes the main suspect.

Two side issues were found while testing:
- **In test mode, etlhub offers a CSB test fixture as `external_data` default for all levels.** fkt runs then get 100 % missing covariates.
- **`validate_inputs` errors are lost in etlhub.** The job message is empty.

## Context

| | |
|---|---|
| Run | COM/Malaria, dry-run cycle `202504`, test mode on |
| Image | `mvevans89/pridec_forecast:1.0.0` (pinned in `etlhub/infrastructure/forecast_runner.py`) |
| INLA | R package 25.06.07, binary reports `GitId: "devel"` |
| Branch | `5-expose-etl-scripts-via-a-fastapi-web-service` |
| Logs | `logs/<job_id>.log` and `.json`, also `GET /api/tracking/etl-logs/<job_id>` |

## Error

INLA runs for 2 to 3 minutes, then the cores abort:

```
GitId: "devel"
Error:2 Reason: Matrix is not (numerical) positive definite
Line:395 Function: GMRFLib_init_problem
Aborted
Error: INLA model failed with error message:
 $ operator is invalid for atomic vectors
In addition: Warning message:
In parallel::mclapply(1:cs$nconfig, (function(k) { :
  all scheduled cores encountered errors in user code
Execution halted
```

The `mclapply(1:cs$nconfig, …)` loop matches `INLA::inla.posterior.sample()`. The error most likely occurs while sampling the posterior, after the fit. The `$` error is a consequence: the failed jobs return error strings.

etlhub records the job as `error` with the container message: correct behaviour. The earlier `Permission denied` on `inla.mkl.run` (#18) is fixed: the binary runs.

## Runs

| Job | Config | external_data | Covariates | INLA weight | Result |
|---|---|---|---|---|---|
| `forecast_74f97408`, `forecast_dcdfce26`, `forecast_01030798` (2026-10-20) | various | — | — | 0.0 | success |
| `forecast_376f57f1`, `forecast_e355375d`, `forecast_aeda1590` (2026-10-21) | test config (`assets/test/inputs/config.json`) | test fixture, 21 orgUnits, **0 / 99 in common** | `wealth_index`, `mosquito_net` **100 % null** | 0.15 | error: positive definite |
| `forecast_22ee563a` (2026-10-21 16:20) | production `assets/forecast_configs/config_malaria.json` | `assets/forecast_configs/external_data_fkt.csv`, **99 / 99** orgUnits | external covariates **0 % null** | 0.6 | error: same |

No run with INLA enabled has ever succeeded with this image.

Config of `forecast_22ee563a` (`input/config_valid.json`):
- `pred_vars`: `net_p2`, `month_since_llin`, `pridec_climate_temperatureMean`, `pridec_climate_mndwi`, `pridec_climate_evi`, `wealth_index`, `pridec_climate_relHumidity`, `pridec_climate_precipitation`
- weights: inla 0.6, glm_nb 0, ranger 0.76, arimax 0, naive 0.3
- `month_analysis` 60, `month_assess` 3, `forecast_start` 202504, `month_lag` 3
- `inla_hyper` filled in by validation

Inputs: 99 orgUnits, 15444 rows. Climate columns are null on about 45 % of the rows: these are the periods that only `external_data` covers (outer join in `validate_inputs`). `polygon_valid.geojson` has 195 polygons, 99 with data.

## Probable causes, in order

1. **INLA binary.** It reports `GitId: "devel"`. Also, `forecast/scripts/install-pridec-packages.R` has this line commented out: `# INLA::inla.binary.install(os="Ubuntu-24.04") #to avoid matrix error messages`.
2. **Parallel posterior sampling.** `inla.posterior.sample` is known to fail this way in some multi-thread setups. This would be fixed with `num.threads = 1`, or `"1:1"`, in the PRIDEC call.
3. **Model specification.** Spatial graph built from 195 polygons while 99 have data, flat priors (`5e-04`), many null climate rows. Not checked: the PRIDEC package code is outside this repo.

## Next steps

- **forecast (Michelle):**
  - Rebuild the image with `INLA::inla.binary.install(os="Ubuntu-24.04")`.
  - Rerun one COM/Malaria forecast with the inputs left in `input/` (they validate).
  - If the error remains, run `inla.posterior.sample` with a single thread, then check the spatial graph (islands, orgUnits without data).
- **PRIDEC:** when an INLA posterior sample fails, report the real error instead of `$ operator is invalid for atomic vectors`.

## Side issue 1: test-mode defaults give fkt runs a CSB fixture

`etlhub/infrastructure/default_files.py` maps `external_data/fkt` and `external_data/csb` to `assets/test/inputs/external_data.csv` in test mode. The comment there already says so: "its orgUnits are the CSB ones, its config needs mosquito_net, so fkt runs fail in the forecast".

As a result:
- In test mode, "Use default" (`POST /input/files/external_data/from-default`) writes that fixture. It was uploaded as `external_data/fkt` on 2026-10-20 16:38.
- The fixture shares no orgUnit with COM.
- The test config needs `mosquito_net`, which `external_data_fkt.csv` does not have. So the test pair cannot be used for fkt runs at all.

`validate_inputs` accepts the empty covariates without warning. The level check of `external_data.csv` is already listed as not done in `known-issues.md` ("Pipeline revision of 2026-10-12").

Proposed:
- Give test mode an fkt fixture, or use the production files for fkt.
- `validate_inputs` should fail, or warn, when a `pred_vars` column is entirely null, or when `external_data` shares no orgUnit with the disease data.

## Side issue 2: `validate_inputs` errors are lost

`etl/scripts/validate_inputs.py` raises `ValidationError(errors=…, messages=…)` without passing a message to `Exception`. So `str(e)` is empty, and etlhub reports `validate_inputs failed: ` with no reason (`etlhub/application/use_cases/etl_use_cases.py:74`).

Seen with `validate_inputs_b6df15e1`. The real error, replayed in memory, was: `ERROR: The following predictor variables are missing from the input datasets:mosquito_net`.

Proposed: etlhub should include `e.errors` in the job message when present. This is an etlhub-only change, since `etl/` is not modified here.

## Current state of the open run

The run is left with the inputs of `forecast_22ee563a`:
- `input/config.json` = production `config_malaria.json`
- `input/external_data.csv` = `external_data_fkt.csv`
- `validate_inputs` = success
- `forecast` = error

## Workaround

Set the `inla` weight to `0` in `config.json`.
