---
name: etlhub-practices
description: "Conventions and best practices for the etlhub FastAPI + Celery + Redis service (PRIDE-C ETL hub). Use whenever you add or change an etlhub endpoint, Celery task, use case, service, job tracking, webhook, WebSocket log stream, auth dependency, Celery or env configuration, logging, or etlhub tests, and whenever you review an etlhub PR. Covers both the conventions that already exist in the code (with real templates) and the best practices the project is still missing (authentication, blocking handlers, silent errors, webhook validation, Celery limits, test reliability), each as a small, safe migration. Use it even if the user does not say 'best practices'."
---

# etlhub — conventions and best practices

Companion to `etlhub/CLAUDE.md` (always-on rules) and to the `etlhub` skill (how the service is built: architecture, endpoint and config tables). Known problems with evidence are in `etlhub/docs/known-issues.md`. This skill answers two questions:

1. **How do I write code that matches what already exists?** → `references/templates.md`
2. **Which good practices are missing, and how do I introduce them without breaking `etlui`?** → `references/migrations.md`

Checklists for new jobs, contract changes and PR reviews: `references/checklists.md`.

Line numbers in the references come from an inspection of the repository. Re-run `grep -n` on the symbol before editing.

## How to work in this repo

1. **Read the template, copy the pattern.** Every job type follows the same five layers (service → use case → Celery task → registry → router). Do not invent a variant.
2. **One concern per change.** A migration from `references/migrations.md` is its own change. Do not mix it with a feature.
3. **Smallest diff.** The project has no linter and little test coverage: large refactors cannot be verified. Prefer additive changes.
4. **Tests first for untested areas.** If you touch something listed as untested in `CLAUDE.md`, add a test in the same change.
5. **Ask before deciding.** Items under "Decisions pending" are product or ops choices. Present the options and wait.

## Existing conventions to keep

- Layers and imports: `api` → `application`, `core` · `application` → `domain` · `infrastructure` → `domain`, `application` · `domain` → nothing. Do not add new violations.
- Singletons (`@lru_cache`) for adapters in `core/dependencies.py`; services are built per request with `Depends()`.
- `job_id = f"{task_type}_{uuid.uuid4().hex[:8]}"`, generated in the service.
- Services only call `task_launcher.launch(...)`. They never touch Celery, Redis, files or events.
- ETL wrappers go through `_execute_etl_job`; failures become `ETLException(f"{name} failed: {e}")`.
- Celery tasks use `_run_task(...)` and **re-raise** after writing the "error" status.
- Launch endpoints: `POST`, `status_code=202`, `response_model=ETLResponse`, `summary`, `description`, `response_description`, optional `webhook_url: str | None = Query(None)`, handler `async def api_<action>`.
- Domain errors map to HTTP in `main.py` (`JobNotFoundError` 404, `ValidationError` 400, `TaskLaunchError`/`ETLException` 500).
- Naming: `*_router.py`, `*_service.py`, `*_use_cases.py`, `run_<action>`, `task_<action>`, `get_<x>_service`. English for code, logs and messages.
- Tests: `app.dependency_overrides` through the `override_dependencies` fixture; assert `202`, `status == "accepted"`, and `job_id` in the body. Task tests monkeypatch `tasks.JobStore` with an in-memory store and `tasks._send_webhook` with a recorder.
- Commits: English, imperative, capitalised (`Add …`, `Refactor …`), no prefix.

## Frozen contracts (`etlui` depends on them)

`ETLResponse = {status, message, job_id, webhook_url}` · `JobStatus = {status, job_id, started, completed, logs, message}` · `job_id = <type>_<8 hex>` · WebSocket types `etl_log_history`, `job_status_update`, `etl_log_entry`, `etl_log_complete`, close code `4004` · webhook payload `{job_id, status, message, logs_url}`. A change here also changes `etlui/src/composables/useWebSocketLogger.ts` and `useEtlPipeline.ts`, in the same change.

## Missing practices — status board

| Practice | Today | Target | Where |
|---|---|---|---|
| Authenticate routers | Only `/api/config/*` and `/auth/me` | All routers except `auth`; per-route on tracking because of the WebSocket | migrations.md#m1 |
| No blocking work in `async def` | `/post_forecast`, `/update_key` run inline | Celery tasks, 202 | migrations.md#m2 |
| No silent failures | `except Exception: pass` in `JobStore`, `tasks.py`, `_JobLogger`, `forecast_runner` | `logger.warning` with context | migrations.md#m3 |
| Validate `webhook_url` | Any URL, any scheme | One validator in `core/webhook.py`, called from `launch()` | migrations.md#m4 |
| Reliable test config | `pytest.ini` ignored; 1 failing test | `[pytest]` header; fix token cache key | migrations.md#m5, #m6 |
| Env loading order | `get_settings()` runs before `load_dotenv()` | One explicit loading path | migrations.md#m7 (decision) |
| Celery limits | Defaults only, no time limit, no retry | Explicit settings | migrations.md#m8 (decision) |
| Layering | `etl_events` imported from `application`/`infrastructure` | `EventPublisher` port injected | migrations.md#m9 |
| Front/back agreement | JSON bodies ignored on `/fetch_disease`, `/validate_inputs` | One agreed shape | migrations.md#m10 (decision) |
| WebSocket loop | Likely busy-wait, race after subscribe | Bounded wait, subscribe before history | migrations.md#m11 |
| Logging | 8 `print(`, no config, most modules have no logger | `logging.getLogger(__name__)` everywhere | migrations.md#m3 |

Suggested order: m5, m6 → m3 → m4 → m2 → m1 → the rest. m5, m6 and m3 are low risk and make the later changes verifiable.

## Decisions pending (ask the user, do not choose)

1. Must the log WebSocket be authenticated? Browsers cannot send an `Authorization` header on a WebSocket: it needs a query token or a first auth message.
2. Should `/` and `/output/*` stay public?
3. With `webhook_allowed_hosts` empty: refuse everything, or only require https? Revalidate in `_send_webhook` against redirects?
4. Env loading: set `ENV_FILE`, point `_PROJECT_ROOT` to the repo root, or call `load_dotenv` first?
5. `/fetch_disease` and `/validate_inputs`: should the backend accept the JSON body, or should the front stop sending it?
6. Webhook payload: absolute `logs_url`? HMAC signature?
7. Celery: `acks_late`, time limits, retries. ETL scripts write to DHIS2 and may not be idempotent, so do not enable retries blindly.
8. Should `GET /api/config/` keep returning `DHIS_TOKEN`? (`etlui` shows it in a password input.)
9. Should the OAuth routes stay? The front never uses them, and the callback validates an OAuth token with `ApiToken`.

## Never

- Call real endpoints against a real DHIS2 or the host (no auth, they write to DHIS2, run `docker run` or `rm -rf output/`).
- Print or copy secrets (`.env`, `.env.debug`, `.gee-private-key.json`): variable names only.
- Add blocking work in a handler, a new `except Exception: pass`, a new `print(` in `etlhub/`, or a new direct `etlhub.api.*` import from `application`/`infrastructure`.
- Treat a green test as proof of Redis behaviour: Redis is a global `MagicMock` in `conftest.py`.