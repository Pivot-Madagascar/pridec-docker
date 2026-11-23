# Pivot imports: fetch, approve per data element, post

Implemented 2026-11-20.

## Why

Since `pivot_dhis_tools` v0.3.0 (etl commit 7ca2d21), the CLI scripts `import_pivot_COM.py` / `import_pivot_CSB.py`
check each data element and ask on the terminal before posting a flagged one. etlhub has no terminal: Michelle's
`import_pivot_*_etlhub.py` fetch and check only, and leave "approve then post" to etlhub (`etl/etlhub-documentation.md`).

## Flow (step data_import)

1. `import_pivot_com` / `import_pivot_csb` (Celery, `application/use_cases/fetch_pivot.py`): `fetch_pivot_*_etlhub`,
   then its items (each element's values and `{text, flagged, error}` check) in Redis, `pivot_fetched:<mode>:<pass>:<task>`
   (`infrastructure/fetched_imports.py`, since 2026-11-23): the next fetch of that import in the pass replaces them
   whole, a new pass starts empty, and they survive a logout and a forecast run's opening (until then, files in the
   mode's `input/temp_fetch`, emptied when a run opened). COM uses the pass's `PARENT_OU`; both read `PIVOT_URL`
   from the editable config (`/api/config`, Redis), `PIVOT_TOKEN` from etlhub's environment. Nothing goes to DHIS2.
2. `GET /pipeline/imports/fetched`: per import, the elements fetched (rows, flagged, message). etlui's
   `ImportApprovalDialog` shows one selectable row each; flagged rows start unchecked. etlui keeps the answer in
   Pinia (`stores/fetchedImports.ts`) and asks again only when a Pivot import finishes, the pass or mode changes, or
   on Refresh.
3. `POST /pipeline/imports/approve` `{decision: "approve", elements: [...]}`: the item `approve_imports` runs as a
   synchronous job (`AnalyticsService.approve_imports`, as `post_forecast`): lock, pass's DRYRUN, journal `launched` with
   `params: {elements}`, then `post_dataElements` per element; success unlocks `build_analytics`.
   `reject` is unchanged (back to pending, `decided` event).

## Decisions

- **The approval is the post** (no new pipeline item): `approve_imports` already sits between the imports and
  `build_analytics`, and `gate.run("approve_imports")` gives the lock, the DRYRUN check and the journal for free.
- **`elements: []` is allowed**: approving without posting (e.g. all flagged, DHIS2 already has the data). It is journaled.
- **A flagged element can be posted**: the user decides, as the CLI's `[y/N]` prompt allowed.
- **Element names are a closed list** (`Literal` of `check_import_availability.COM_ELEMENTS + CSB_ELEMENTS`): they become
  file names. An element without its file in this pass: 409 before the gate (nothing written).
- **A failed post fails the job** (`approve_imports` error): HTTP errors (`raise_for_status` in the library) and an
  import status `ERROR` in DHIS2's answer. Elements posted before it stay; posting again is safe (`CREATE_AND_UPDATE`).
- etlhub does not import the `_etlhub` scripts: their `from config import` needs `etl/scripts` on `sys.path` (absent in
  the worker) and reads `PARENT_OU` from `.env`. `fetch_pivot.py` is a copy (`ponytail:` comment).

## Known limits

- A new pass empties `input/`: an import **carried over** from an earlier pass has no file here. Approving its
  elements gets 409 until it is launched again (when both imports are carried, `approve_imports` is carried too).
- Relaunching an import after the approval does not reset `approve_imports` (as before): the new data is not posted
  until the user approves again (`confirm=true`).
- The import status check reads DHIS2's `status` / `response.status` / `conflicts`; not checked against a real DHIS2.
