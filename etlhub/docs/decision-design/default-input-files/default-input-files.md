# Default input files

> Since 2026-10-15. Code: `etlhub/infrastructure/default_files.py`, `InputUploadService` (`save_default`, `defaults`,
> `default_path`), `api/routers/input_router.py`. Tests: `etlhub/tests/api/test_default_files.py`.

A forecast run needs a `config.json` per disease and an `external_data.csv` per org unit level
(see [../pipeline-checkpoints/pipeline-checkpoints.md § 4.6](../pipeline-checkpoints/pipeline-checkpoints.md)). The user can upload their own files, or use the
**default file** etlhub offers for that item. A default is **offered, never applied automatically**: the user
clicks "Use default".

## Where the defaults come from

The defaults are files of the repository, under `assets/`. Each mode has its own set:

| Item | Production (`DRYRUN=false`) | Test mode (`DRYRUN=true`) |
|---|---|---|
| `config/Malaria` | `assets/forecast_configs/config_malaria.json` | `assets/test/inputs/config.json` |
| `config/Diarrhea` | `assets/forecast_configs/config_diarrhea.json` | `assets/test/inputs/config.json` |
| `config/Respinf` | `assets/forecast_configs/config_respiratory.json` | `assets/test/inputs/config.json` |
| `external_data/fkt` (ADJ, COM) | `assets/forecast_configs/external_data_fkt.csv` | `assets/test/inputs/external_data.csv` |
| `external_data/csb` (CSB) | `assets/forecast_configs/external_data_csb.csv` | `assets/test/inputs/external_data.csv` |

The mapping is `SOURCES` in `default_files.py`. `test_every_repo_default_exists` fails if a file is renamed.

### Known inconsistency in test mode (kept on purpose)

`assets/test/inputs/` is a **CSB/Malaria** test set, and test mode offers it for **every** disease and level:

- its `external_data.csv` has the 21 CSB orgUnits and **none** of the 195 fokontany ones;
- its `config.json` needs `mosquito_net` in `pred_vars`, a column that only this test CSV has.

In a test-mode **ADJ or COM** run (fokontany) with these defaults, the external columns are empty (NaN) after the
merge in `validate_inputs`. `validate_inputs` only checks NAs in `external_data` *before* the merge, so the
validation probably passes and the failure comes later, in the R forecast. This comes from reading the code: it was
not run. Upload matching files for fokontany runs in test mode.

The test `config.json` uses 5 models (inla, glm_nb, ranger, arimax, naive). It replaces the earlier decision to use
a `forecast_assets/test_config.json` (Ranger + Naive) in test mode: that file never existed.

## Storage: the `default_files` table

```sql
CREATE TABLE default_files (
    mode TEXT, item TEXT, hash TEXT,     -- production | test, config/<disease> | external_data/<level>, sha256
    filename TEXT, path TEXT, size INTEGER, seeded_at TEXT,
    PRIMARY KEY (mode, item, hash)
);
```

- Same SQLite file as the checkpoints (`logs/etlhub.db`), **in both modes**. It is never in the test-mode Redis blob,
  which is rewritten at each transaction and would carry 9 MB of CSV otherwise. The table holds metadata only; the
  content stays in `assets/` (`path` is relative to `assets/`).
- **Seed**: once per etlhub process, at the first use of the defaults (`get_default_files()`). For each item, etlhub
  hashes the file of `assets/`. When the hash differs from the current default, it records a row.
- **The latest repository file wins.** The default offered is the latest row (`seeded_at`) of `(mode, item)`.
  After a `git pull` that changes `config_malaria.json`, the new content becomes the default at the next restart;
  the old hash stays as history. Going back to an earlier content makes its row the latest again.
- **Limit**: only the hash of an old default is kept, not its content (`ponytail:` in the code). The content will be
  copied to `data/defaults/<hash>` when admins can replace a default
  ([../pipeline-config/pipeline-config.md](../pipeline-config/pipeline-config.md), phase 4). Rule planned then: the most recent default wins,
  whether it comes from the repository or from an admin upload.
- **A missing file** is logged (`ERROR`, "Default … not found") and etlhub starts anyway. That item gets no default:
  no "Use default" button, uploads still work.

## API

| Method & path | Does |
|---|---|
| `GET /input/defaults` | Defaults of the current mode: `{item: {filename, size}}`. A missing file is left out. |
| `GET /input/defaults/{config\|external_data}/{key}/preview?limit=100` | Same answer as `/input/files/*/preview`, for the default of `config/<key>` or `external_data/<key>`. 404 when there is none. |
| `POST /input/files/{config\|external_data}/from-default` | Copies the default of the **open run's** item into `input/`, through the same path as an upload: checks, `forecast_start` written into `config.json`, pipeline lock, checkpoint, `?confirm=true` rule (R5), copy kept in `uploads/<cycle>/`. 409 without an open run, 404 when the item has no default. |

## Interface (etlui)

Under each `FileDropzone` of a `DiseaseCard` (its `config.json` and the 2 shared `external_data.csv`):
"Default · *filename* · *size*", with **Preview** (always available) and **Use default** (enabled only when the
upload is, i.e. a run of that disease or level is open). The server file shown after "Use default" is the same as
after an upload: nothing says it came from the default.

## Deployment

etlhub must reach `assets/` **in production too**. Paths are resolved from the repository root
(`Path(__file__).parents[2] / "assets"`), not from the working directory. There is no etlhub Dockerfile today; if
etlhub is containerized, mount `assets/` (read-only is enough).
