# Forecast sandbox

Status: implemented (2026-11-25). Not in production until one test-mode forecast has run in the sandbox (below).

## Problem

The API and the worker ran as a user of the `docker` group. That group is root on the host.

- **The API faces the Internet.** Code execution in the API or in one of its dependencies therefore gave root on the host.
- **The forecast container got a lot.** It received the whole `.env` (`REDIS_PASSWORD`, `PIVOT_TOKEN`, GEE)
  through `/tmp/forecast_<id>.env` (known-issues §1.10), and it ran with `--network host`, so it could reach
  Redis, which holds the DHIS2 token, and the API.
- **The image was pinned by tag only.** It comes from a personal Docker Hub account, and a tag can be pushed again.

## Decision

1. **Sandboxed `docker run`** (`infrastructure/forecast_runner.py`) with these settings:
   - `--network none`;
   - no `--env-file`;
   - `--cap-drop ALL --cap-add SYS_NICE` and `--security-opt no-new-privileges`;
   - `FORECAST_IMAGE` = tag plus digest;
   - unchanged: `--user` set to the worker's uid, and `input/` mounted read-only.

   `_build_dynamic_env_file` is deleted.
2. **A queue of its own.** `celery_app.task_routes` sends `task_forecast` to the queue `forecast`.
   `run_celery` without `-Q` serves `celery,forecast`, so development, e2e and a single worker are unchanged.

## Evidence that the R pipeline needs neither env nor network

- **This repository, `forecast/`.** It has no `Sys.getenv`. The network appears only in the image build scripts
  (CRAN, GitHub, INLA).
- **The `PRIDEC` package** (GitHub `Pivot-Madagascar/PRIDEC-package`, HEAD `c0e1996` of 2026-11-24):
  - it has no `Sys.getenv`;
  - its only network call is `get_dhis_data` (httr2), which `forecast/` never calls;
  - the Quarto templates use `embed-resources: true`.
- **What remains [Likely], not proven.** The `1.1.0` image installed `PRIDEC` from GitHub at build time, possibly
  an older commit. `DRYRUN` was already documented as unread by the R code (`dry-run.md`), and `PARENT_OU` and
  `LOG_LEVEL` were passed without any reader found.

**Check before production:** one full forecast in test mode, with the report. If it fails for lack of
network or of a variable, the error names it. The fix is then that variable alone, through `-e NAME`, never the
whole `.env`.

## Residual risks

- **Whoever holds `REDIS_PASSWORD` can queue forecasts.** The worker's input is limited to Celery JSON messages
  (registered tasks only), and those cannot choose the image or the mounts.
- **Stopping during a forecast.** Stopping the worker during a forecast loses its logs and its end, and leaves the
  pipeline lock held.
- **No resource limit yet.** `--memory` and `--pids-limit` are not set until a real run is measured (INLA threads
  count as pids).
- **Rejected options:**
  - a Docker socket proxy filters routes, not request bodies, so creating a container with `/` mounted stays possible;
  - rootless Docker needs fuse-overlayfs and a second store for the 3 GB image, and `SYS_NICE` has no effect there.
