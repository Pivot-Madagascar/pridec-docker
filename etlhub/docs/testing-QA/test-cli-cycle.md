# CLI cycle test (`./pridec`-style, without etlhub)

> **First run: 2026-10-22**, branch `5-expose-etl-scripts-via-a-fastapi-web-service`, against the local DHIS2
> (`http://localhost:8082`, 2.40.3). Results in [§ 5](#5-results-of-the-2026-10-22-run).

| § | Content |
|---|---|
| 1 | What this test checks |
| 2 | Safety first |
| 3 | Prerequisites |
| 4 | The test, step by step |
| 5 | Results of the 2026-10-22 run |
| 6 | Problems found |
| 7 | Clean up |

---

## 1. What this test checks

Since 2026-10-22, `etl/scripts/config.py` exists in two versions:

- **CLI** (the file on its own): every value comes from the environment / `.env`, `-e` beats `.env`, never Redis,
  never `etlhub`;
- **etlhub** (`etlhub/script_config.py`, plugged in by `etlhub/__init__.py`): editable keys from Redis, DHIS2 URL and
  token from the etlui login.

This test runs one forecast cycle **the way the CLI does** (`./pridec` → `docker compose run`, as in
`pivot_forecast.sh`), with an `etl` image **built from this branch**, and checks that:

1. the image runs without `etlhub` or `redis` installed;
2. `-e` values beat `.env` (`pivot_forecast.sh` passes `DISEASE_CODE` / `OU_LEVEL` with `-e`);
3. the old module API still works (`config.dryRun`, `config.DISEASE_CODE`, ...);
4. each step of phases 2 and 3 runs: `validate_inputs` → `forecast` → `post_forecast` → `build_analytics` →
   `update_key`.

It does **not** cover phase 1 (`import_gee`, `import_pivot_com`, `import_pivot_csb`) nor the `fetch_*` steps: the
inputs come from `assets/test/inputs/` instead.

How each step maps to `pivot_forecast.sh`:

| `pivot_forecast.sh` | This test |
|---|---|
| `source .env`, `rm -rf input output`, copy `forecast_assets/config_*.json` | a temporary working directory with its own `.env`, `input/` filled from `assets/test/inputs/` |
| `jq` sets `forecast_start` | not needed: the test `config.json` already has `"forecast_start": "202601"` (the value `pivot_forecast.sh` uses in `test` mode) |
| `pridec etl fetch_disease / fetch_climate / fetch_geojson` | skipped (test inputs) |
| `pridec etl validate_inputs`, `pridec forecast forecast` | same, through `docker compose run` |
| `pridec etl calc_orgUnit_alerts` | skipped: the command does not exist in `etl/cli.sh` |
| `pridec etl post_forecast -e DRYRUN=true` | same |
| phase 3: `build_analytics`, `update_key` | same, with `-e DRYRUN=true` (**see § 2 for `update_key`**) |

Why not `./pridec` itself: the repo's `pridec` has a hard-coded `COMPOSE_FILE` (another machine), and the `pridec`
installed in `~/bin` may point to another clone. The test runs the same command `pridec` builds:
`HOST_PWD=<dir> docker compose -f compose.yaml run --env-from-file <dir>/.env -e ... --rm <service> <task>`.

## 2. Safety first

- **Run it against the local test DHIS2 only**, never a real instance, and with `DRYRUN=true`.
- **`update_key` writes to DHIS2 even with `DRYRUN=true`.** `pivot_dhis_tools` v0.1.2 `pridec_update_key` only
  logs its `dryRun` flag, then always sends the `PUT /api/33/dataStore/pridec/pridec_update`. Step 4.9 is
  therefore commented out: run it only if overwriting that key on the target DHIS2 is acceptable.
- `post_forecast` with `DRYRUN=true` sends `POST /api/dataValueSets?dryRun=true`: DHIS2 checks the data and saves
  nothing.
- `build_analytics` with `DRYRUN=true` makes no DHIS2 call.
- **Secrets**: the temporary `.env` holds a DHIS2 token. Never print it (`cat .env`), keep it out of the repo, and
  revoke the token at the end (step 4.10). The `tester` password is typed at a prompt, never written to a file.

## 3. Prerequisites

- Docker and Docker Compose v2, `jq`, `curl`.
- `test-venv` at the repo root (Python 3.12 with etlhub's requirements): used only to create and revoke the DHIS2
  token with etlhub's own functions.
- The local DHIS2 running on `http://localhost:8082` with the PRIDE-C metadata, and the `tester` account.
- The image `mvevans89/pridec_forecast:1.0.0` (the one etlhub runs). `compose.yaml` still names `0.1.0`; the
  override in step 4.2 replaces it.

## 4. The test, step by step

Run the blocks in order, in one bash shell, from the repo root.

### 4.1 Variables and the `etl` image

```bash
R=$(pwd)                                   # repo root
W=$(mktemp -d /tmp/pridec-cli-test.XXXX)   # temporary working directory (HOST_PWD)
DHIS2=http://localhost:8082

# Build etl/ from this branch under a test tag: the published 0.1.0 image is the old code and stays untouched.
docker build -t pridec_etl:cli-test etl/
```

The build takes a few minutes (it installs `pridec_gee` and `pivot_dhis_tools` from GitHub).

### 4.2 The working directory

```bash
mkdir -p "$W/input" "$W/output"
chmod 777 "$W/input" "$W/output"           # the containers write there as root

# Temporary .env: the run values. DHIS_TOKEN is filled in step 4.3.
( umask 077; cat > "$W/.env" <<EOF
DHIS_URL=$DHIS2
DHIS_TOKEN=
DRYRUN=true
LOG_LEVEL=INFO
PARENT_OU=VtP4BdCeXIo
OU_LEVEL=5
EOF
)

# Test inputs: simulated data, 21 CSB orgUnits under VtP4BdCeXIo (level 5), periods 202101-202612.
cp "$R"/assets/test/inputs/* "$W/input/"
chmod 644 "$W"/input/*

# compose.yaml bind-mounts .gee-private-key.json (create_host_path: false): an empty placeholder, GEE is not used.
: > "$W/.gee-private-key.json"

# Use the branch image for etl and forecast 1.0.0, without editing compose.yaml.
cat > "$W/compose.override.yaml" <<'EOF'
services:
  etl:
    image: pridec_etl:cli-test
  forecast:
    image: mvevans89/pridec_forecast:1.0.0
EOF

# What ./pridec does: compose.yaml with HOST_PWD = the working directory, .env passed with --env-from-file.
run() { HOST_PWD="$W" docker compose -f "$R/compose.yaml" -f "$W/compose.override.yaml" \
          run --env-from-file "$W/.env" --rm "$@"; }
```

Why the test `config.json` and not `assets/forecast_configs/config_malaria.json`: `config_malaria.json` needs
climate variables (`pridec_climate_evi`, `relHumidity`, `precipitation`, `net_p2`, ...) that the test data does not
have, so `validate_inputs` would fail.

### 4.3 A short-lived DHIS2 token for `tester`

The token in the root `.env` may be expired: on 2026-10-22 it got a 401. Create a 1-hour personal access token with
the functions etlhub uses at login (`etlhub/api/auth/dhis2_auth.py`), and write it into the temporary `.env` without
printing it:

```bash
read -rsp "Password of DHIS2 user tester: " DHIS2_TEST_PASSWORD; echo
DHIS2_TEST_PASSWORD="$DHIS2_TEST_PASSWORD" W="$W" DHIS2="$DHIS2" "$R/test-venv/bin/python" - <<'EOF'
import os, re, time, httpx
from pathlib import Path
from etlhub.api.auth.dhis2_auth import create_pat

w, url = Path(os.environ["W"]), os.environ["DHIS2"]
with httpx.Client(timeout=15) as c:
    key, uid = create_pat(c, url, ("tester", os.environ["DHIS2_TEST_PASSWORD"]), int(time.time() + 3600) * 1000)
(w / "pat_uid").write_text(uid)
env = w / ".env"
env.write_text(re.sub(r"^DHIS_TOKEN=.*$", "DHIS_TOKEN=" + key, env.read_text(), flags=re.M))
print("token created, uid", uid)
EOF
```

### 4.4 Check `config` inside the image

```bash
run -e OU_LEVEL=6 -e DISEASE_CODE=pridec_historic_CSBMalaria --entrypoint python etl -c "
import sys, importlib.util, scripts.config as c
print('etlhub/redis loaded:', [m for m in sys.modules if m == 'redis' or m.startswith('etlhub')])
print('etlhub installed:', importlib.util.find_spec('etlhub') is not None, '| redis installed:', importlib.util.find_spec('redis') is not None)
print('OU_LEVEL (-e 6, .env 5):', c.get_ou_level(), '| DISEASE_CODE:', c.DISEASE_CODE, '| dryRun:', c.dryRun, '| PARENT_OU:', c.PARENT_OU)
print('DHIS_URL set:', bool(c.DHIS_URL), '| DHIS_TOKEN set:', bool(c.DHIS_TOKEN))
"
```

Expected: nothing loaded, nothing installed, `OU_LEVEL` = `6` (`-e` wins), `dryRun` = `True`, both DHIS2 values set.
The token is never printed, only whether it is set.

### 4.5 `validate_inputs`

```bash
run -e DISEASE_CODE=pridec_historic_CSBMalaria -e OU_LEVEL=5 etl validate_inputs
ls "$W/input"
```

Expected: `SUCCESS: All inputs valid.`, and `config_valid.json`, `input_valid.json`, `polygon_valid.geojson` in
`input/`.

### 4.6 `forecast`

```bash
run -e DISEASE_CODE=pridec_historic_CSBMalaria -e OU_LEVEL=5 forecast forecast 2>&1 | tee "$W/forecast.log" | tail -5
jq '.dataValues | length' "$W/output/forecast.json"
jq -r '[.dataValues[].dataElement] | unique | .[]' "$W/output/forecast.json"
```

Expected: `SUCCESS: Forecast created` and `SUCCESS: HTML report created at output/forecast_report.html`.
`output/forecast_report.html` can be opened in a browser, as `pivot_forecast.sh` asks before posting.

### 4.7 `post_forecast` (dry run)

```bash
run -e DRYRUN=true etl post_forecast
```

Expected with the current test data: **409** (see § 6.2). A 401 means the token is not valid (step 4.3).

### 4.8 `build_analytics` (dry run)

```bash
run -e DRYRUN=true etl build_analytics
```

Expected: `DRY RUN - analytics tables will not be built`, no DHIS2 call.

### 4.9 `update_key` (writes to DHIS2, see § 2)

```bash
# Writes the dataStore key pridec/pridec_update even with DRYRUN=true. Uncomment only if that is acceptable.
# run -e DRYRUN=true etl update_key
```

### 4.10 Revoke the token

```bash
DHIS2_TEST_PASSWORD="$DHIS2_TEST_PASSWORD" W="$W" DHIS2="$DHIS2" "$R/test-venv/bin/python" - <<'EOF'
import os, re, httpx
from pathlib import Path
from etlhub.api.auth.dhis2_auth import revoke_pat

w = Path(os.environ["W"])
with httpx.Client(timeout=15) as c:
    ok = revoke_pat(c, os.environ["DHIS2"], (w / "pat_uid").read_text().strip(),
                    auth=("tester", os.environ["DHIS2_TEST_PASSWORD"]))
print("revoked:", ok)
env = w / ".env"
env.write_text(re.sub(r"^DHIS_TOKEN=.*$", "DHIS_TOKEN=", env.read_text(), flags=re.M))
EOF
unset DHIS2_TEST_PASSWORD
```

## 5. Results of the 2026-10-22 run

| Step | Result |
|---|---|
| 4.1 build | OK, `pridec_etl:cli-test` (741 MB) |
| 4.4 `config` in the image | OK: no `etlhub` / `redis` installed or loaded; `-e OU_LEVEL=6` beat `.env`'s `5`; `dryRun`, `DISEASE_CODE`, `PARENT_OU` read through the old API |
| 4.5 `validate_inputs` | OK: the 3 validated files written, 21 orgUnit polygons |
| 4.6 `forecast` (1.0.0) | OK in 27 s; `forecast.json` = 3906 values, 3 data elements `pridec_forecastal_CSBMalaria{Avg,LowCI,UppCI}`, periods 202102-202603; 21 R warnings, not read |
| 4.7 `post_forecast` | First with the root `.env` token: **401**. With a `tester` token: **409** (§ 6.2). Nothing written |
| 4.8 `build_analytics` | OK, no DHIS2 call |
| 4.9 `update_key` | Exit code 0 and **the key was written** on the local DHIS2 (`wMYPz2_updated_2026-10-22`) although `DRYRUN=true` (§ 6.1) |
| 4.10 revoke | OK (HTTP 200) |

Not run: phase 1, the `fetch_*` steps, `calc_orgUnit_alerts`. The image was not pushed; `compose.yaml` still uses
the published `mvevans89/pridec_etl:0.1.0`.

## 6. Problems found

1. **`update_key` ignores `DRYRUN`.** In `pivot_dhis_tools` v0.1.2 (`pridec/update_dataStoreKey.py`), `dryRun`
   only logs "Conducting a dryRun. dataStore key will not be updated." and the `requests.put` always runs. This
   affects the CLI and etlhub (both call `pridec_update_key`).
   `dry-run-merge.md` § 9 says the opposite and is wrong on this point. Possible fix: skip the call in
   `etl/scripts/update_pridec_key.py` when `DRYRUN` is true, as `build_analytics.py` does, and fix the library.
2. **The test data posts unknown codes.** `assets/test/inputs/disease_data.json` (from
   `assets/test/create-test-input.py:277`) uses `pridec_historical_CSBMalaria`; the real code is
   `pridec_historic_CSBMalaria`. The forecast derives `pridec_forecastal_*` from it, which DHIS2 does not know
   (it has `pridec_forecast_CSBMalaria*`): 409. The 21 orgUnits and the category option combo `pridec_COC_u5` exist.
   Renaming `historical` to `historic` in the test data should let the dry-run POST through (not tried).
3. **`update_key` returns exit code 0 on failure** (a 401 was only logged as `ERROR`). With `pridec` always ending
   with `exit 0`, a failed step never stops `pivot_forecast.sh`.
4. **`calc_orgUnit_alerts`**, called by `pivot_forecast.sh` for CSB runs, is not a command of `etl/cli.sh`.
5. The `etl` and `forecast` containers write `input/` and `output/` as root: see § 7 to delete them.

## 7. Clean up

```bash
# Files written by the containers belong to root: delete them from a container.
docker run --rm -v "$W:/w" alpine sh -c 'rm -rf /w/input /w/output'
rm -rf "$W"
docker image rm pridec_etl:cli-test
```
