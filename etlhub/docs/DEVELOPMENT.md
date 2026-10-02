# etlhub — development method

> Measured on 2026-10-02 from the git history and from local runs (`test-venv`). Section 1 describes what **is**. Section 2 holds rules for **new code**: they are **proposals** until the team confirms them, and must not be read as a description of current practice.

## 1. What the project does today (measured)

### Tests and history

- 36 commits touch `etlhub/` (8 earlier ones lived under `web/`). 22 of them change source code outside `tests/` and `docs/`: **6 include tests in the same commit, 16 do not**. The 1f82acb "SOLID" refactor (+432 lines, 25 files) contains no test.
- **No commit adds a test before the code it tests** (0 cases). The 9 test-only commits all follow their code. Inside the 6 mixed commits the order of writing is invisible: git keeps only the final state. So test-first is neither documented nor demonstrable from the history.
- The first `etlhub/tests/` appear on 2026-06-05 (7th commit), are deleted on 2026-06-15 by the rename, and the current suite dates from 2bb9e4e (2026-07-03).
- af608d9 (forecast fixes) contains the fix and `test_forecast_task.py` together; whether the test came first is unknown.
- Branches are named `<issue number>-<slug>`; merge messages cite PR numbers; commits cite no issue.

### The suite

- 31 tests: 29 pass, 1 fails depending on order (module-level `_token_cache`; it passes alone), 1 integration test is deselected. About 1.5 s.
- **Coverage of the sources: 58 %** (domain 100 %, core 87 %, api 60 %, application 55 %, infrastructure 37 %). Below 60 %: `forecast_runner` 12 %, WebSocket `etl_logs` 17 %, `job_store` 25 %, `forecast_report_router` 27 %, `validation_use_cases` 28 %, `etl_use_cases` 38 %, `request_tracker` 50 %, `config_store` 51 %, `analytics_service` 55 %, `validation_service` 56 %, `auth/router` 57 %, `tasks` 57 %. `run_server.py` and `run_celery.py` are at 0 %.
- 18 of 31 tests assert only on `status_code` (1.84 assertions per test on average).
- No real dependency: `redis`, `pridec_gee`, `pivot_dhis_tools`, `earthengine_api` and `geopandas` are replaced in `sys.modules`. 25 `MagicMock`, 6 `AsyncMock`, 25 `patch`, 8 `monkeypatch`, 7 `dependency_overrides`; no `tmp_path`, no `fakeredis`.
- **Side effect:** because Redis is mocked, `RequestTracker` falls back to files, so each run writes about 119 files in `logs/requests/` at the repository root (git-ignored).
- CI runs `pytest --cov` with no threshold and no linter. Branch protection is not visible in the repository. There is no pre-commit, no git hook, no PR template, no CODEOWNERS.
- Front end: one spec file (8 tests), no `test` script, no eslint, no prettier.

### Clean architecture

- The domain imports only `typing` and `pydantic`.
- 5 ports exist. `JobRepository`, `TaskLauncher`, `WebhookNotifier` and `RequestTrackerProtocol` are injected but also bypassed (`JobStore()` in `tasks.py`, `_send_webhook()`, `get_request_tracker()`). `EventPublisher` has no explicit implementer and is never injected.
- Imports that cross the written rule: `application` → `api` (deferred, `etl_use_cases.py:40`), `infrastructure` → `api` (deferred, `tasks.py:52,79`, `forecast_runner.py:172,177`), `api` → `infrastructure` without injection (`middleware.py:12`, `config_router.py:9`), `api` → `etl.scripts`, `application` → `etl.scripts` (11 imports). Widespread but not covered by the written rule: `api` → `domain` (5 files), `infrastructure` → `core` (4), `application` → `core` (2); `core/dependencies.py` is the composition root.
- SOLID, as visible in the code. **S**: one service per functional area, but `tasks.py` mixes Celery tasks, webhooks, status and events, and `run_rscript` is 104 lines. **O**: a job is one entry in `CeleryTaskLauncher._registry`, but also a method in a service and an import in `etl_use_cases.py`. **I**: ports are small, except `JobRepository.load_from_file`. **D**: services depend on `Protocol`s, with the bypasses above. **L**: no violation shown.

### Clean code

- 56 files, 2,715 lines, 158 functions; no file over 200 lines.
- Longest: `get_home_html` 168 (HTML), `run_rscript` 104 (branch count ≈ 24), `run_validate_inputs` 78 (≈ 17, 8 parameters), `get_dhis2_user_info` 71 (≈ 23).
- 42 `except Exception`, 21 of them with only `pass`; 8 `print(`; 18 one-letter names; no `# noqa`, no `# type: ignore`.
- Return type annotated: api 27 %, application 82 %, infrastructure 50 %, core and domain 100 %. Docstrings: 7 on 158 functions. Code and logs are in English.
- Duplicates: 8 identical 4-line service methods, `post_forecast` / `update_key`, `_get_redis` twice.
- No linter, formatter, type checker or hook is configured.

## 2. Rules for new code (proposed, to be confirmed)

**Tests**
1. Behaviour and its test ship in the same commit. This is the only rule the history can verify.
2. For a new endpoint, task, service, or a bug fix, write the failing test first, make it pass, then refactor. Git cannot prove it. For a bug fix, run the test once without the fix and say so.
3. Assert behaviour (body fields, stored state, webhook payload), not only `status_code`.
4. A test must not write into the repository. Point `LOGS_DIR` to `tmp_path` (not set up yet).
5. A test must pass alone and in any order: clear module-level caches (`_token_cache`, `get_settings.cache_clear()`).
6. Do not lower the coverage of a file you touch.
7. A refactor ships with tests that pin the behaviour first (1f82acb did not).

**Architecture**
8. No new import from `application` or `infrastructure` to `api`. Inject ports instead of instantiating adapters.
9. Tolerated until the team decides otherwise: `api` → `domain` DTOs, any layer → `core` settings, `core/dependencies.py` as composition root, `application` → `etl.scripts` wrappers.

**Clean code (new or changed functions)**
10. At most 50 lines, 10 branches and 4 parameters. Existing functions above that are debt, not a precedent.
11. No `except … pass`: log with the job id. No `print(` except job output inside `capture_stdout`.
12. Annotate parameters and return type. Add a docstring only when the reason is not obvious.
13. Do not copy a duplicated block: extend the registry or extract a helper.
14. English for identifiers, comments and logs.

## 3. How to check

```bash
cd etlhub
export COVERAGE_FILE=/tmp/etlhub.coverage          # keep the coverage file out of the repository
../test-venv/bin/python -m pytest tests -m "not integration" -p no:cacheprovider \
  --cov=. --cov-report=term-missing
```

`pytest-cov` is installed in `test-venv`. Expect the `logs/requests/` side effect until rule 4 is applied. No linter is installed: do not add one without asking.

## 4. Decisions needed

- Is test-first a rule for all new code, or only for endpoints and Celery tasks? Is "test in the same commit" enough?
- Are the numeric limits in rules 10 to 12 acceptable?
- Which of the tolerated imports in rule 9 become official?
- Add a linter or formatter (for example ruff) and a pre-commit hook? A coverage threshold in CI?
- Fix the `logs/requests/` side effect in `conftest.py`?
- Add tests to `etlui` (a `test` script, more specs)?