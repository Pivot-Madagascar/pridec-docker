# Pipeline checkpoints: target design

> **Status (2026-10-12)**
>
> - **Design revised on 2026-10-12** to align with the reference documentation (`pivot_forecast.sh`):
>   see "Changes since the 2026-10-09 version" at the end of the [diagrams](pipeline-checkpoints-diagrams.md).
> - **Implemented in etlhub**: the 2026-10-09 version (3-step path, forecast runs (R6), input files per run,
>   approval, invalidation of dependents within a run, confirmation of relaunches (R5), monthly cycle,
>   global lock without expiry), plus the 2026-10-12 revision except steps 19 and 20 and the level check of
>   `external_data` (§8). Code: `domain/pipeline.py`, `infrastructure/checkpoint_store.py`,
>   `api/routers/pipeline_router.py`. Tests: `tests/infrastructure/test_checkpoint_store.py`, `tests/api/test_pipeline_router.py`.
> - **etlui**: done (§8, steps 12 and 21), checked with a mocked API only.
> - **To do**: `calc_orgunit_alerts` (step 19), the test-mode scope (step 20), the level check of
>   `external_data`, and the open points (§6).
>
> Reference: the reference documentation (`pivot_forecast.sh`) is authoritative for the workflow (3 phases, `pridec`
> commands, step order). etlhub/etlui is its **manual** version: the user triggers each action and uploads their own
> files; the server adds the control layer (lock, checkpoints, cycles, confirmations).

## Agreed rules

| Rule | Content |
|---|---|
| **R1** | Every item is mandatory. `config.json` is **one item per disease** (`config/<disease>`), shared by its 3 runs. `external_data.csv` is **one item per level** (`external_data/fkt`, `external_data/csb`). Both are uploaded from the user interface. |
| **R2** | An item can be launched only if all its **prerequisites** are in `success`. |
| **R3** | Only one job at a time (global lock). **The lock never expires**: only `DELETE /pipeline/lock` frees it. |
| **R4** | A step is valid (`done`) only if all its items are in `success` **and** the previous step is valid. Otherwise the following steps are not accessible. |
| **R5** | Undoing what was validated (relaunching an item in `success`, replacing a file already validated, reopening a closed run) needs `confirm=true`, given after an impact dialog. |
| **R6** | Only one **forecast run** open at a time. A run handles one source × disease pair, from the first fetch to `post_forecast`. |
| **Cycle** | A monthly run named after the calendar month (`YYYYMM`). It opens at the first launch of the month and closes once the 3 steps are valid. When the month changes, the next cycle starts automatically; an unfinished cycle stays unfinished, and its open run is abandoned. **Chosen cycle**: `PUT /pipeline/cycle` `{"cycle": "YYYYMM" | null}` (etlui: month input next to "Cycle") sends every launch, run, upload and approval to that cycle, and `GET /pipeline/checkpoints` shows it by default. `null` or the current month = follow the calendar month again (the default). Refused (409) for a future month, while a job runs, or while a run is open in the current cycle. A complete cycle can be chosen but takes no launch. A chosen past month does not follow the calendar: it stays until changed. Kept per mode (test mode forgets it). The ETL scripts do not read the cycle: it only files the checkpoints, the uploads and `forecast_start`. |
| **Test mode** | etlui "Test mode" button (`PUT /pipeline/mode`): `DRYRUN=True` passed to `import_gee` and `post_forecast`, checkpoints kept **in Redis only**. Going back to production erases this data, with `confirm=true` if there is any (§4.10). |

The server enforces all these rules: otherwise it answers **409** (422 for an `external_data.csv` that does not
match the run's level), and a refusal writes nothing. **All API messages are in English.**

---

## 1. The problem, in one line

Before this work, the UI's ✓ meant "the API answered 202", not "the job finished in `success`".
This state lived in Vue `ref`s (`results`, `climateSuccess`…), so it disappeared on page reload
and in another browser.

---

## 2. The target path

| # | Step | Frequency | Items | Order |
|---|---|---|---|---|
| ① | `data_import` | once a month, before the forecasts | `import_gee`, `import_pivot_com`, `import_pivot_csb`, `approve_imports` (decision), `build_analytics` (5 items) | Imports in any order; `approve_imports` after the 2 pivot imports; `build_analytics` after `import_gee` and `approve_imports` |
| ② | `forecast` | 9 runs a month, one per source × disease pair | 3 `config/<disease>`, 2 `external_data/<level>`; per run: 3 `fetch_*`, `validate_inputs`, `forecast`, `calc_orgunit_alerts` (CSB only), `approve`, `post_forecast` (71 items) | See §4.2. Runs in any order, only one open at a time (R6) |
| ③ | `system_update` | once a month, after the 9 `post_forecast` | `build_analytics`, `update_key` | Fixed |

Sources: `ADJ`, `COM`, `CSB`. Diseases: `Malaria`, `Diarrhea`, `Respinf`
(`etlui/src/stores/forecastConfig.ts`).

What changes compared with the base 4-step path:
- `external_upload` is no longer a step: input files are uploaded during the runs. `config.json` once
  per disease (3 uploads), `external_data.csv` once per level (2 uploads: fokontany for ADJ and COM, CSB),
  then copied back into `input/` automatically for the other runs that share them;
- the preparatory jobs (`fetch_*`, `validate_inputs`) become tracked items;
- approval becomes a mandatory checkpoint, in phase 1 (`approve_imports`) as in each run (`approve`);
- `post_forecast` moves into each run ("Forecasts → PRIDE-C");
- CSB runs have one more item, `calc_orgunit_alerts` (command `pridec etl calc_orgUnit_alerts`).

`build_analytics` must go through the etlhub API: launched manually from the DHIS2 interface, etlhub does not see it and
step ① stays invalid.

---

## 3. What we keep from the "stages" philosophy (`lang` project), and what we change

| Principle in `lang` | What it becomes in etlhub |
|---|---|
| **The server is the only source of truth**; the client only displays | ✅ Kept. Checkpoints and runs live in etlhub (SQLite), not in Pinia or localStorage. |
| **One question only: "where am I?"** | ✅ Kept. `GET /pipeline/checkpoints` returns the whole state, open run included. |
| **Progress persisted and resumable** | ✅ Kept. Tables without TTL. |
| **Closed vocabulary** | ✅ Kept: `pending` (no row), `running`, `success`, `error`. |
| **The client names the step, the server checks it** | ✅ Kept. The server resolves the checkpoint at launch (§4.4). |
| **Path definition separate from the engine** | ✅ Kept. A Python module declares items and prerequisites. |
| **The state is an agenda** | ❌ **Changed.** We store facts and compute progress. |
| **Moving forward = an action in the request** | ❌ **Changed.** We move forward when a job finishes, often asynchronously. |

> **We store one fact per item ("CSB/Malaria:forecast: success, job X, at such time"),
> and we *compute* the state on every read.**
> A step is valid when all its items are in `success` and the previous one is valid.
> The current step is the first one that is not.

---

## 4. Design

### 4.1 The tables (`logs/etlhub.db`)

```sql
-- One fact per item: the latest status overwrites the previous one.
CREATE TABLE IF NOT EXISTS checkpoints (
    cycle      TEXT NOT NULL,   -- '202610'
    step       TEXT NOT NULL,   -- data_import | forecast | system_update
    item       TEXT NOT NULL,   -- 'import_gee', 'config/Malaria', 'external_data/fkt', 'CSB/Malaria:forecast'…
    job_id     TEXT,            -- NULL for a decision; 'upload_config_…' for an upload
    status     TEXT NOT NULL,   -- running | success | error
    updated_at TEXT NOT NULL,
    PRIMARY KEY (cycle, step, item)
);

-- Context of the forecast runs (R6). These are not checkpoints.
CREATE TABLE IF NOT EXISTS forecast_runs (
    cycle         TEXT NOT NULL,
    couple        TEXT NOT NULL,   -- 'CSB/Malaria'
    state         TEXT NOT NULL,   -- open | closed | abandoned
    disease_code  TEXT NOT NULL,   -- 'pridec_historic_CSBMalaria'
    ou_level      TEXT NOT NULL,   -- '6' (ADJ, COM) | '5' (CSB)
    alert_name    TEXT,            -- 'CSBMalariaVigilance' (CSB only)
    opened_at     TEXT NOT NULL,
    closed_at     TEXT,
    PRIMARY KEY (cycle, couple, opened_at)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_run ON forecast_runs(state) WHERE state = 'open';
```

- An item **without a row** is `pending`. Resetting an item to `pending` = deleting its row.
- The `pipeline_lock` table (global lock, R3) does not change. An upload also takes the lock:
  that is why it carries a technical `job_id` (`upload_config_…`, `delete_external_data_…`).
- Uploaded files are also kept in `<data_dir>/uploads/<cycle>/` (`config_<disease>.json`,
  `external_data_<fkt|csb>.csv`), since `input/` is emptied at each run. A new cycle starts without files.
- Databases created before 2026-10-12 also have a `forecast_runs.external_data` column (`DEFAULT 'none'`): unused, inserts skip it.
- These tables are **not** subject to the `RETENTION_DAYS` of `request_log`. The detailed history stays in `request_log` and `logs/`.

### 4.2 The path definition: items and their prerequisites

An ordered list is no longer enough (free order here, fixed there). Each item declares its prerequisites **within its step**;
the order between steps comes from R4. The real code is in `domain/pipeline.py` (`run_context`, `run_items`,
`PIPELINE`, `progress`, `launchable`, `blocking_reason`, `dependents`, `resolve_slot`). In short:

```python
SOURCES = ("ADJ", "COM", "CSB")
DISEASES = ("Malaria", "Diarrhea", "Respinf")
COUPLES = [f"{s}/{d}" for s in SOURCES for d in DISEASES]
OU_LEVEL = {"ADJ": "6", "COM": "6", "CSB": "5"}
LEVEL = {"ADJ": "fkt", "COM": "fkt", "CSB": "csb"}

def config_item(couple: str) -> str:
    return f"config/{couple.split('/')[1]}"                # one upload per disease, shared by its 3 runs

def external_data_item(couple: str) -> str:
    return f"external_data/{LEVEL[couple.split('/')[0]]}"  # one upload per level

def run_items(couple: str) -> dict[str, list[str]]:
    c = couple
    items = {
        f"{c}:fetch_disease": [],
        f"{c}:fetch_climate": [],
        f"{c}:fetch_geojson": [],
        f"{c}:validate_inputs": [config_item(c), external_data_item(c), f"{c}:fetch_disease",
                                 f"{c}:fetch_climate", f"{c}:fetch_geojson"],
        f"{c}:forecast": [f"{c}:validate_inputs"],
    }
    last = f"{c}:forecast"
    if c.startswith("CSB/"):
        items[f"{c}:calc_orgunit_alerts"] = [last]
        last = f"{c}:calc_orgunit_alerts"
    items[f"{c}:approve"] = [last]                # human decision
    items[f"{c}:post_forecast"] = [f"{c}:approve"]
    return items

PIPELINE = {   # step → {item: prerequisites}
    "data_import": {
        "import_gee": [], "import_pivot_com": [], "import_pivot_csb": [],
        "approve_imports": ["import_pivot_com", "import_pivot_csb"],      # human decision
        "build_analytics": ["import_gee", "approve_imports"],
    },
    "forecast": {**{f"config/{d}": [] for d in DISEASES},                  # 3 configs
                 **{f"external_data/{l}": [] for l in ("fkt", "csb")},     # + 2 external_data
                 **{k: v for c in COUPLES for k, v in run_items(c).items()}},   # + 66 = 71 items
    "system_update": {
        "build_analytics": [],
        "update_key": ["build_analytics"],
    },
}
```

`progress()` is chained (R4) and returns `done`, `accessible` and, for each item, `launchable`
(step accessible, prerequisites in `success`, and for step ②: item of the open run).

Step ② has **71 items**: 3 `config/<disease>`, 2 `external_data/<level>`, 6 ADJ and COM runs of 7 items,
3 CSB runs of 8 items.

### 4.3 The forecast runs (R6)

The 9 runs share the same files (`input/`, `output/`). Two interleaved runs would produce a forecast on
another pair's data. Hence only one run open at a time, guaranteed by the `one_open_run` index
and checked before the insert.

**Open**: `POST /pipeline/runs` with `{source, disease}`. The server, in a single transaction:
1. checks R3 (lock free), R4 (step ② accessible) and R6 (no run open, otherwise 409
   `Run CSB/Malaria is open: finish or abandon it first`);
2. if this pair already has a closed run in the cycle, requires `confirm=true` (R5) and resets all the pair's items to `pending`;
3. empties `input/` and `output/` (like `pivot_forecast.sh`); if emptying fails, the run is not opened;
4. copies back into `input/` the files already uploaded for the pair's disease and level;
5. records the `open` run with its frozen context (`run_context`).

**During the run**: every step ② job belongs to the open run. At the launch of each step ② job,
the server writes the run's `DISEASE_CODE` and `OU_LEVEL` into the dynamic config (Redis `app:config:dynamic`),
where `etl/scripts/config.py` reads them; `ALERT_NAME` is written there for CSB runs and cleared otherwise.
If the write fails, the launch is refused and nothing is written. etlui sends nothing, and the Admin page is no longer
used to change pairs. A step ② job without an open run → 409.

**Close**: automatically, when the run's `post_forecast` reaches `success`. Another pair can then be opened.

**Abandon**: `DELETE /pipeline/runs/current`. The run becomes `abandoned`,
its items go back to `pending`, nothing is published. An abandoned pair reopens without confirmation.

### 4.4 Linking a job to its checkpoint: at launch

`CeleryTaskLauncher.launch` calls `start()`, which writes the item as `running` with the job's `job_id`.
At the end of the job, `finish(job_id, status)` finds the row by the `job_id` column (nothing is added to `job:{id}`).
The checkpoint is resolved by `resolve_slot` **at launch**, then frozen (cycle included: a job launched in October
and finished in November stays in the October cycle).

- **Step ② jobs**: the item is `{pair of the open run}:{job name}`.
- **`build_analytics`** has two slots (`data_import:build_analytics`, `system_update:build_analytics`).
  `resolve_slot` picks, in path order, the **first launchable slot** (`launchable`) that is not
  in `success`. If there is none, it picks the last launchable slot in `success`, which triggers R5.
- No `?step=` parameter: the etlui contract does not change for launches.

### 4.5 Who writes the statuses

- **Celery jobs**: `_update_task_status` (`infrastructure/tasks.py`) calls `finish()` for `success` and `error`,
  `task_forecast` included.
- **Synchronous jobs**: `post_forecast` and `update_key` go through `PipelineGate.run()` in `AnalyticsService`,
  `success` after running, `error` if it raises. `calc_orgunit_alerts`: Celery or synchronous, to be decided (§6).
- **Uploads**: `PipelineGate.change_input()` in `InputUploadService`, under the lock.
- **Decisions**: `approve` through `PipelineGate.decide()` (`POST /pipeline/runs/current/approve`),
  `approve_imports` through `PipelineGate.decide_imports()` (`POST /pipeline/imports/approve`); direct write (`job_id = NULL`).
- **Closing the run**: in `finish()`, when the finished item is a `post_forecast` in `success`.

### 4.6 The input files (uploaded from the user interface)

The user picks their own files on their computer, or uses the **default file** of the item (files of `assets/`,
copied into `input/` only when the user clicks "Use default"): see [../default-input-files/default-input-files.md](../default-input-files/default-input-files.md).

| File | Item | Rules |
|---|---|---|
| `config.json` | `config/<disease>`, **mandatory**, **one per disease** | Uploaded in the first run of the disease (open run, otherwise 409). The server writes `forecast_start` into it, as `jq` does in `pivot_forecast.sh` (value to confirm, §6). Copied back into `input/` when the disease's 2 other runs open. The interface shows the expected file: `config_malaria.json`, `config_diarrhea.json`, `config_respiratory.json` (for `Respinf`). |
| `external_data.csv` | `external_data/<level>`, **mandatory**, **one per level** (`fkt`: ADJ and COM; `csb`: CSB) | Open run, otherwise 409. File must match the run's level, otherwise 422 (columns to specify, §6). Copied back into `input/` when the other runs of the same level open. |

Replacing or deleting either file:
- **as long as it has not been used** (the open run's `validate_inputs` not in `success`, and no other run that shares it
  has its `forecast` in `success`): free;
- **otherwise**: needs `confirm=true` (R5). **Only the open run** goes back to `pending` from `validate_inputs` on.
  The other runs that used the old file keep their `success` (they are already published); the `impact`
  lists them in `stale_runs`.

Deleting a file resets its item (`config/<disease>` or `external_data/<level>`) to `pending`.

### 4.7 The approvals

**`approve_imports`** (step ①): after `import_pivot_com` and `import_pivot_csb`, the user checks that COM cases
are < 100 and CSB cases < a limit (to be set, §6), then approves. `build_analytics` requires it.
`{"decision": "reject"}` sends the approval back to `pending`.

**`approve`** (each run): after `forecast` (and `calc_orgunit_alerts` for CSB), the user reads
`output/forecast_report.html`, then:
- `POST /pipeline/runs/current/approve` with `{"decision": "approve"}`: `{couple}:approve` → `success`,
  which unlocks `post_forecast`;
- `{"decision": "reject"}`: `forecast` and its dependents (`calc_orgunit_alerts`, `approve`) go back to `pending`.
  The user fixes the problem (for example a new file, with confirmation) and relaunches, without confirmation for the forecast;
- or abandons the run (§4.3).

### 4.8 Relaunches, invalidations and confirmations (R5)

**In an open run**, everything relies on the same files. Relaunching or replacing an item therefore resets to `pending`
**all the run items that depend on it** (transitive closure of the prerequisites, `dependents()`). Without this, one could
approve a forecast computed on old inputs.

**Between steps**, it is the opposite: the `success` statuses of the following steps **stay in the database** (R4). They no longer count
until the previous step is revalidated, then count again without relaunching anything. Items of steps ① and ③
do not invalidate their dependents (relaunching `import_gee` leaves `build_analytics` in `success`).

| Action | Confirmation | Effect |
|---|---|---|
| Relaunch an item in `error` or `pending` | No | Item → `running` |
| Relaunch an item in `success` | `confirm=true` | Item → `running`, its run dependents → `pending` |
| Replace or delete a file already used (§4.6) | `confirm=true` | Open run: `validate_inputs` and dependents → `pending`; other runs: unchanged, listed in `stale_runs` |
| Reject the forecast | No (it is the decision itself) | `forecast` and dependents → `pending` |
| Reopen a pair already closed | `confirm=true` | All the pair's items → `pending`, `input/` and `output/` emptied |
| Relaunch a step ① item during step ② | `confirm=true` | Step ① not valid → steps ② and ③ not accessible, open run blocked |

Without `confirm=true`, the server answers **without writing anything**:

```json
{
  "code": "confirmation_required",
  "message": "CSB/Malaria:forecast is already in success: resend with confirm=true to relaunch it",
  "impact": {
    "item": "CSB/Malaria:forecast",
    "step": "forecast",
    "current_step": "forecast",
    "reset_items": ["CSB/Malaria:calc_orgunit_alerts", "CSB/Malaria:approve"],
    "blocked_steps": ["system_update"],
    "kept_items": {"system_update": 0}
  }
}
```

`reset_items` only lists the dependents that have a row (the others are already `pending`).
etlui builds the impact dialog **only** from `impact`, requires the checkbox
"I have read the impact and I approve this update", then resends the same request with `confirm=true`.

### 4.9 Reading

`GET /pipeline/checkpoints?cycle=202610`:

```json
{
  "cycle": "202610",
  "current_step": "forecast",
  "run": {"cycle": "202610", "couple": "CSB/Malaria", "state": "open",
          "disease_code": "pridec_historic_CSBMalaria", "ou_level": "5", "alert_name": "CSBMalariaVigilance",
          "opened_at": "…"},
  "lock": null,
  "steps": [
    {"step": "data_import", "done": true, "accessible": true, "items": [
      {"item": "import_gee", "status": "success", "job_id": "import_gee_ab12cd34", "updated_at": "…", "launchable": true}
    ]},
    {"step": "forecast", "done": false, "accessible": true, "items": [
      {"item": "external_data/csb", "status": "success", "job_id": "upload_external_data_…", "updated_at": "…", "launchable": true},
      {"item": "CSB/Malaria:forecast", "status": "running", "job_id": "forecast_…", "updated_at": "…", "launchable": true}
    ]},
    {"step": "system_update", "done": false, "accessible": false, "items": []}
  ]
}
```

`launchable` ignores the lock: a running item stays `launchable`; `lock` says that a job is running.
etlui calls this route on mount and on each `etl_log_complete` or `job_status_update` received on the WebSocket.
It computes nothing: it shows the ✓, greys out what is not `accessible` or `launchable`, and shows the pair
of the open run above the file pickers.

---

### 4.10 Test mode

The etlui "Test mode" button (`test = YES`) switches etlhub to test mode.

- **Switch**: `PUT /pipeline/mode` `{"dry_run": true | false}`, with `?confirm`. Refused (409) while a job runs.
- **Effect on the jobs** (target, step 20 not done: today `DRYRUN` applies to every script): the mode passes `DRYRUN=True`
  to `import_gee` (quick partial import) and to `post_forecast` (no write to PRIDE-C). Not to be confused with the `DRYRUN`
  option of each `pridec` command, whose effect varies from one command to another. Test mode offers `assets/test/inputs/config.json`
  as the default `config.json` ([../default-input-files/default-input-files.md](../default-input-files/default-input-files.md)).
- **Storage in test mode**: the same SQL logic runs on an **in-memory** SQLite database, serialized into the Redis key
  `pipeline:dry_run:db` (under the Redis lock `pipeline:dry_run:lock`). Nothing is written to `logs/etlhub.db`, and
  production is neither visible nor changed. Files uploaded in test mode go to `uploads/dry_run/`.
- **Cycle in test mode**: the real month, with the same rules (R1 to R6).
- **Back to production**: the Redis key and `uploads/dry_run/` are erased. If there is test data,
  `confirm=true` is required; otherwise 409 `confirmation_required` with
  `impact = {mode, items_in_success, open_run}`.
- **Limit**: the `input/` and `output/` files are shared between the two modes: opening a test run empties them too.

---

## 5. Decisions

| Question | Decision |
|---|---|
| Workflow reference? | The reference documentation (`pivot_forecast.sh`) is authoritative for the phases, commands and order. etlhub only adds the control layer. |
| What is a cycle? | The monthly run, named after the calendar month (`YYYYMM`), opened by the server at the first launch, closed when the 3 steps are valid. A launch in a closed cycle of the same month → 409 `Cycle 202610 is complete…`. **Month change: automatic switch**; the previous cycle stays unfinished if it was not finished, its open run is abandoned. |
| Another month? | **Chosen cycle**: `PUT /pipeline/cycle` `{"cycle": "YYYYMM" | null}` (etlui: month input next to "Cycle") sends every launch, run, upload and approval to that cycle, and `GET /pipeline/checkpoints` shows it by default. `null` or the current month = follow the calendar month again (the default). Refused (409) for a future month, while a job runs, or while a run is open in the current cycle. A complete cycle can be chosen but takes no launch. A chosen past month does not follow the calendar: it stays until changed. Kept per mode (test mode forgets it). The ETL scripts do not read the cycle: it only files the checkpoints, the uploads and `forecast_start`. |
| Test mode? | `PUT /pipeline/mode`. `DRYRUN=True` passed to `import_gee` and `post_forecast`; checkpoints in Redis only; back to production with confirmation, test data erased (§4.10). |
| Block or warn? | Block, server side (409). A block only in the UI could be bypassed. |
| Import order? | Free; `approve_imports` after the 2 pivot imports; `build_analytics` after `import_gee` and `approve_imports`. |
| Phase 3? | `build_analytics` → `update_key`, as in the reference. |
| Input files? | Uploaded from the user interface, all mandatory. `config.json` **one per disease** (3 uploads), `forecast_start` written by the server; `external_data.csv` **one per level** (2 uploads), level checked. Copied back into `input/` for the runs that share them. Replacing a file already used only invalidates the open run. |
| Choice of the pair? | When the run opens. `DISEASE_CODE`, `OU_LEVEL`, `ALERT_NAME` are injected by the server. |
| Approval? | Mandatory: `approve_imports` before `build_analytics` (step ①), `approve` before `post_forecast` (each run). Forecast rejected → `forecast` to redo. |
| Failure and relaunch? | The latest status wins. Undoing a `success` needs a confirmation (R5). Within a run, dependents are invalidated; between steps, `success` statuses are kept. |
| Stuck lock? | **It never expires.** `DELETE /pipeline/lock` frees it; the `running` item then becomes `error`. |
| Message language? | **English**, for all API messages (409, 422). |
| `calc_orgunit_alerts`? | Active item of the CSB runs, between `forecast` and `approve` (command `pridec etl calc_orgUnit_alerts`). |

---

## 6. Open points and known limits

Open points:

| Point | Question |
|---|---|
| `forecast_start` | Which value does `jq` write in `pivot_forecast.sh` (current month, next month, last month of data)? The server must write the same one. |
| `approve_imports` | What is the limit for CSB cases? |
| `approve_imports` role (to be determined, 2026-10-26) | Its buttons are now under the import availability report ([../import-availability/import-availability.md](../import-availability/import-availability.md)). Still open: should it close step ① (after `build_analytics`) instead of gating `build_analytics`? Should etlhub refuse it (409) while the report shows missing data, or keep it a free human decision? Should it also need `import_gee`? Should its journal event keep which report (section check times) it was made on? Nothing changed: today it needs `import_pivot_com` and `import_pivot_csb` only and does not read the report. |
| Test mode and `forecast` | Decided 2026-10-15: test mode offers `assets/test/inputs/config.json` as default ([../default-input-files/default-input-files.md](../default-input-files/default-input-files.md)). |
| `calc_orgunit_alerts` | Celery or synchronous job? What exactly does it publish? |
| Level check for `external_data` | Which columns distinguish an fkt file from a csb file? |

Limits:
- **Matching `config.json`**: the server cannot check that the file matches the run's disease,
  unless the file contains a field that allows it.
- **`build_analytics` launched outside etlhub** (DHIS2 interface) is not seen: step ① stays invalid.
- **Reopened run**: forecasts already published in PRIDE-C stay there until the new `post_forecast` replaces them.
- **A killed worker blocks everything** until `DELETE /pipeline/lock`: the lock never expires.
- **Run context in Redis**: the Admin page can still change `DISEASE_CODE` or `OU_LEVEL` between two jobs;
  the server rewrites them at the launch of each step ② job, but not while a job runs.
- **Unfinished cycle**: at the end of the month, a cycle not finished stays unfinished; nothing finishes it for you.
- **Test mode**: `input/` and `output/` are shared by both modes.
- `DELETE /output/reset` and jobs launched from the command line (`./pridec`, `pivot_forecast.sh`) bypass all these controls.

---

## 7. What we do not add

- No state machine engine or workflow library: a dict of prerequisites and a few pure functions (`progress`, `launchable`, `dependents`, `resolve_slot`).
- No path definition in the database: it is versioned code.
- No progress state in Pinia or localStorage.
- No `stale` or `invalidated` status: `done`, `accessible` and `launchable` are computed.
- No automatic copy from `assets/`: its files are offered as defaults, used only on "Use default".
- No lock expiry.

---

## 8. Implementation order

✅ = done (base 2026-10-08 → 09; 2026-10-09 version; 2026-10-12 revision). ⬜ = to do.

1. ✅ `domain/pipeline.py`, `infrastructure/checkpoint_store.py` (`checkpoints`, `pipeline_lock`, `BEGIN IMMEDIATE`).
2. ✅ `CeleryTaskLauncher.launch()` → `start()`; `_update_task_status` → `finish()`.
3. ✅ `AnalyticsService` and `InputUploadService` go through `PipelineGate`.
4. ✅ `GET /pipeline/checkpoints`, `DELETE /pipeline/lock`, API tests.
5. ✅ Monthly cycle, 422 check of `config.json`, chained `progress()` (R4), confirmation (R5).
6. ✅ **3-step definition**: `PIPELINE` by prerequisites, `launchable()`, `resolve_slot` for the slots of
   `build_analytics`. Lock expiry removed.
   Migration: rows of the old steps match no item and are ignored; the current cycle
   of a development database therefore starts again from `data_import`.
7. ✅ **Runs (R6)**: `forecast_runs` table, `POST /pipeline/runs`, `DELETE /pipeline/runs/current`, injection of
   `run_context` (through the dynamic config), emptying of `input/` and `output/`, closing by `post_forecast`.
8. ✅ **Files**: `config/<disease>` as an item (one per disease), `external_data.csv` per level (optional in that version),
   kept in `uploads/<cycle>/` and copied back into `input/` when the runs that share them open; replacement: only the open run is invalidated.
9. ✅ **Approval**: `POST /pipeline/runs/current/approve` (approve / reject); `post_forecast` requires `approve`.
10. ✅ **Invalidation within the run**: dependents reset to `pending`, and `reset_items` in `impact`.
11. ✅ **`calc_orgunit_alerts`**: route `POST /calc_orgunit_alerts` answering 501; the item exists for the CSB runs.
12. ✅ **etlui** (`usePipeline`, `ModeToggle` before step ①, `ForecastRuns`, `ImpactDialog`): reads the route, no ✓ computed locally anymore; choice of the pair and opening of the run;
    file pickers under the displayed pair; approval screen with the report and the CSV state;
    409 messages; impact dialog on `confirmation_required` then resend with `confirm=true`.
13. ✅ **Documentation**: endpoint table, `ARCHITECTURE.md`, `CLAUDE.MD`, `known-issues.md`, guide and diagrams.
14. ✅ **Automatic month switch** and **test mode** (`PUT /pipeline/mode`, checkpoints in Redis, confirmed exit).
15. ✅ **Phase 3**: `system_update` = `build_analytics` → `update_key`; `calc_csb_alerts` and `build_analytics_after_alerts` removed (2 slots for `build_analytics`).
16. ✅ **`approve_imports`**: decision item in `data_import`, prerequisite of `build_analytics`;
    `POST /pipeline/imports/approve` (`approve` / `reject`). The CSB limit is not checked by the server: the user checks it.
17. ✅ **`external_data/<level>`**: mandatory item, prerequisite of `validate_inputs`; `forecast_runs.external_data` removed
    (existing databases keep the column, unused). ⬜ Level check at upload (422): waiting for the columns that distinguish fkt and csb (§6).
18. ✅ **`forecast_start`**: written by the server when `config.json` is uploaded (end of the 422 refusal). Temporary value: the cycle
    (current month), like the `validate_inputs` default; to align with `pivot_forecast.sh` once confirmed (§6).
19. ⬜ **`calc_orgunit_alerts`**: wire the command `pridec etl calc_orgUnit_alerts` (end of the 501). Blocked: no script
    exists in `etl/scripts/`.
20. ⬜ **Test mode**: `DRYRUN=True` passed to `import_gee` and `post_forecast` only, distinct from the commands' `DRYRUN` option.
    Waiting for a decision: the other jobs would then write to DHIS2 in test mode, and the mode itself is read from `DRYRUN` today.
21. ✅ **etlui**: expected file per disease (`config_respiratory.json` for `Respinf`), `external_data` upload per level, `approve_imports` decision.

---

## 9. The sentence to remember

> **In etlhub, we store *what happened*
> (one fact per item) and we compute *where we are*.**
> The server decides, the client displays. A step only counts if the one before counts,
> one run at a time handles a pair from end to end, and undoing what was validated
> needs the user's explicit agreement.
