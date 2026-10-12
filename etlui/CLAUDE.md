# etlui

## Purpose

Vue 3 + TypeScript front-end (Vite 7, Pinia 3, vue-router 4, axios, Tailwind 4, `vue3-hot-toast`) that drives the PRIDE-C pipeline. It calls the REST API of `etlhub` (port 8111) and follows jobs over its log WebSocket. It has no backend of its own: in production it is static files served by nginx.

## Module map

- `src/composables/` — `usePipeline.ts` (the pipeline checkpoints of etlhub: reads `GET /pipeline/checkpoints` + `/input/files`, polls every 3 s while a job holds the lock, runs every action and keeps a 409 `confirmation_required` in `pending` until the user confirms, then resends with `confirm=true`), `useWebSocketLogger.ts` (log WebSocket client), `useNotification.ts` (toasts through `vue3-hot-toast`), `useActivityLog.ts` (recent activity list, `ActivityEntry` type), `useInputPreview.ts` (preview of those files, from the server or from the selected `File`)
- `src/stores/` (Pinia) — `auth.ts` (DHIS2 user only, persisted in `localStorage`; the session is an HttpOnly cookie JavaScript cannot read), `config.ts` (dynamic config through `configService`), `useTrackingStore.ts` (request tracking; `TrackerView` uses `storeToRefs`, loads the last 50 requests on mount and on Refresh only, no polling, 10 per page client-side; only requests with a `job_id` get a Detail button (and a clickable row); the detail modal shows Method, Status, URL, Duration and Job ID in a one-row table; when the request has a `job_id`, the job logs load right below it via `GET /api/tracking/etl-logs/{job_id}`)
- `src/services/` — `api.ts` (axios instance with `withCredentials: true` + 401 → `/login` except on `/auth/login`, `trackingApi`, `RequestLog` type, `withConfirm` and `errorMessage` helpers — tests that mock `@/services/api` spread `importOriginal()` to keep them), `auth.ts` (`login(dhis2Url, username, password)` → `POST /auth/login`, `logout` → `POST /auth/logout`), `config.ts` (`configService` for `/api/config`), `inputs.ts` (`uploadInputFile` → multipart `POST /input/files/{name}`, `getInputFiles` → `GET /input/files`, `deleteInputFile` → `DELETE /input/files/{name}`, `getConfigPreview`, `getExternalDataPreview` → `GET /input/files/*/preview`)
- `src/views/` — `Dashboard/` (dashboard; `components/` holds the pipeline UI — `ModeToggle` (test mode = `DRYRUN`, shown before step 1), `Accordion` (the 3 steps), `ActionCard`, `ForecastRuns` (step 2: the 9 runs, open/abandon, files, jobs, approval), `ImpactDialog` (R5 confirmation modal built from `impact`), `RecentActivity`, `ForecastReportModal` — and the input-file UI — `FileDropzone`, `PreviewDialog`, `ConfigPreview`, `CsvPreview`, `ConfirmDialog`; the three dialogs wrap `BaseDialog` (native `<dialog>` + `showModal`, shared box/backdrop CSS)), `TrackerView/` (request tracking, `RequestTable`, `RequestDetail`, `JobLogsPanel` — job logs + live WebSocket follow for one `jobId`, also used by `RecentActivity`'s Detail button), `LogsStreamPage.vue` (live logs), `Auth/` (`LoginForm`, `ParametersPage`), `Admin/ConfigView.vue`
- `src/router/index.ts` — routes + global guard (`meta.public`, redirect to `Login`)
- `src/types/` — `config.ts` (`ConfigResponse`), `inputs.ts` (`InputName`, `ServerFile`, `CsvPreviewData`, `ConfigData`)
- `src/config/pipeline.ts` — display of each checkpoint as an `ActionCard` (label, icon) and `jobOf` (checkpoint → job route). No rule: statuses, `launchable` and order come from etlhub
- `src/services/pipeline.ts` + `src/types/pipeline.ts` — `/pipeline/*` routes and job launches, with `confirm`
- `src/utils/preview.ts` — pure helpers, no I/O: streaming CSV parser (`createCsvParser`, `previewCsvStream`, same output shape as etlhub's preview), `formatPeriod`, `formatCell`
- `src/components/` — `Drawer.vue`, `Icons/` (inline SVG paths, `Icon` + `ICONS`). `src/styles/base.css`.
- Tests: `__tests__/*.spec.ts` next to the code (`router/`, `services/`, `composables/`, `utils/`). `vitest.config.ts`: `happy-dom`, `globals: true`, `src/test/setup.ts` (fresh Pinia before each test).

Siblings in the repo:
- `etlhub/` is the only backend. Endpoint table: `.claude/skills/etlhub/references/reference.md`.
- `etl/` and `forecast/` are never called directly: always through `etlhub`.

## Rules

- **The `etlhub` contracts are frozen** (copied from `etlhub/CLAUDE.MD`): `ETLResponse` = `{status, message, job_id, webhook_url}`. `JobStatus` = `{status, job_id, started, completed, logs, message}`. `job_id` = `<task_type>_<uuid4 hex[:8]>`. WebSocket messages: `etl_log_history`, `job_status_update`, `etl_log_entry`, `etl_log_complete`, close codes `4004` (unknown job) and `4401` (no session: `useWebSocketLogger` clears the store and goes to `/login`). Any change must be mirrored in `etlui/src/composables/useWebSocketLogger.ts` and `usePipeline.ts` / `services/pipeline.ts` in the same change, and on the `etlhub` side too. Never change a contract on one side only.
- **Never trigger real jobs against a real DHIS2 or the host** from the dev UI without explicit approval. The dashboard buttons call `/import_*`, `/build_analytics`, `/post_forecast`, `/update_key` (write to DHIS2), `/forecast/` (`docker run`), `DELETE /output/reset` (`rm -rf output/`) and `POST` / `DELETE /input/files/{name}` (overwrite or delete files in `input/`). Use an `etlhub` running with `DRYRUN=true`. Tests mock `@/services/api` (or the service module), never a real backend.
- **Layering**: `views` → `composables` / `stores` → `services` → `types`. `router` only reads `stores/auth`. HTTP calls (`axios`, `fetch`) live in `services/` only. The WebSocket lives in `useWebSocketLogger.ts` only. Views do not import `@/services/*`; they go through a composable or a store. Existing violations are known debt (see Gotchas): do not add new ones, do not refactor them unless asked.
- **Composables orchestrate, they hold no business rules.** The pipeline rules (order, run context, cycle, confirmations) live in etlhub (`etlhub/docs/pipeline-checkpoints.md`); etlui only shows `GET /pipeline/checkpoints` and never computes a ✓. A composable calls a service, updates state, notifies. Follow `usePipeline.ts` / `useInputPreview.ts` (service calls only, typed).
- **No long blocking `await`.** A launch endpoint returns 202 with a `job_id`. Never wait for a job to finish inside a click handler: follow it through the WebSocket or a polling loop that stops on `success` / `error`.
- **Never print or copy secrets.** Do not log the token, `DHIS_TOKEN` or the `Authorization` header. Mention variable names only (`VITE_API_BASE_URL`, `VITE_DHIS2_URL`).
- **Never hardcode a DHIS2 URL or the API URL.** Use `import.meta.env.VITE_*`. The only allowed literal is the existing `http://localhost:8111` fallback; do not add new copies of it (there are already four: `services/api.ts`, `services/auth.ts`, `App.vue`, `LogsStreamPage.vue`).

## Gotchas

- **Pipeline (since 2026-10-09)**: every launch can answer 409 `{message}` (order, lock, no open run) or 409 `{code: 'confirmation_required', message, impact}`; `usePipeline` shows the first and opens `ImpactDialog` for the second. `DISEASE_CODE` / `OU_LEVEL` come from the open run (server side): etlui sends none. Opening a run (`POST /pipeline/runs`) **empties `input/` and `output/`** on the server. The test mode button calls `PUT /pipeline/mode` (DRYRUN); leaving it discards the test checkpoints.
- **Pipeline revision (2026-10-12)**: step 1 has the `approve_imports` decision (`POST /pipeline/imports/approve`, Approve / Reject buttons, not a card); `external_data/<fkt|csb>` is a mandatory item shown with its status (the run no longer has an `external_data` field); the run shows the expected config file per disease (`CONFIG_FILES` in `src/config/pipeline.ts`); step 3 is `build_analytics` → `update_key`. Still pending in etlhub: `calc_orgunit_alerts` (501) and the test-mode scope (`etlhub/docs/pipeline-checkpoints.md` §8).
- **WebSocket `4004`** (since 2026-10-08) means **unknown job** only. A pending or running job without logs yet gets an empty `etl_log_history` and stays open, so `useWebSocketLogger` follows it from the 202 on. Forecast logs still arrive only at the end: during a forecast you see status updates, not log lines. `useWebSocketLogger` defaults its base URL to the axios `baseURL` and maps `https` to `wss`. The tracking page uses it in the request detail modal for pending/running jobs.
- Login: the DHIS2 token stays in etlhub; the browser only holds the `etlhub_session` cookie (HttpOnly, SameSite=Strict, Secure). Every request to etlhub must send credentials (`withCredentials` / `credentials: 'include'`), and POST/PUT/DELETE must come from `FRONTEND_URL` (etlhub checks `Origin`). `ConfigView.vue` shows the DHIS2 URL and token status read-only. Every etlhub route except login/logout needs the session, the log WebSocket included.
- `services/api.ts` defaults `baseURL` to the absolute `http://localhost:8111`, so the Vite proxy (`/api`, `/auth` → `:8111`) is bypassed in dev and `etlhub` must allow CORS (it does, `api/middleware.py`). Most endpoints (`/import_*`, `/fetch_*`, `/forecast`, `/output`, `/input`) are not in the proxy anyway.
- `vite.config.ts` sets `envDir: '../../'`, i.e. the **parent of the repo**, not the repo root. The root `.env` defines `VITE_*` variables, but Vite does not read them from there (read from the config, not executed).
- Ports: Vite dev uses its default (5173, no `port` set). nginx listens on **8000**, but the `Dockerfile` says `EXPOSE 8111` (the API port). The `etlui` service is commented out in `compose.yaml`.
- A 401 from any axios call clears the store and does a hard `window.location.href = '/login'`.
- The drawer (`App.vue` `navItems`) links to `/forecast`, which has no route.
- Toasts: `useNotification().showNotification` calls `vue3-hot-toast` directly.
- There is no TS type for `ETLResponse` or `JobStatus`: responses are read untyped (`response.data?.job_id`).
- Views importing services (layering debt): `api` called directly in `Dashboard/components/ForecastReportModal.vue`; `@/services/auth` in `Auth/LoginForm.vue` (`login`) and `Auth/ParametersPage.vue` (`logout`); `RequestLog` type imported from `@/services/api` in `TrackerView/`.
- `useActivityLog()` creates a new list on every call: `usePipeline` takes the page's `addActivity` as a parameter.
- The `api` instance defaults to `Content-Type: application/json`, which makes axios serialize a `FormData` as JSON. Pass `multipart/form-data` explicitly for uploads (see `services/inputs.ts`).

## Commands

Run from `etlui/`. Yarn 1 is the package manager (`yarn.lock`; the `Dockerfile` runs `yarn install --frozen-lockfile`). There is no `package-lock.json`: do not create one.

- Install: `yarn install`
- Dev: `yarn dev` (Vite; needs `etlhub` on `:8111`, proxy `/api` and `/auth`)
- Build: `yarn build` (output `dist/`, git-ignored). `vite build` does **not** type-check.
- Preview: `yarn preview`
- Tests: `yarn vitest run` (there is no `test` script). 11 files, 67 tests, all passing.
- One file: `yarn vitest run src/composables/__tests__/usePipeline.spec.ts`
- Type-check, linter, formatter, coverage: none installed (`vue-tsc`, ESLint, Prettier and `@vitest/coverage-*` are absent). Do not invent one.
- Docker: `docker build -t etlui etlui/` → nginx on 8000.

## Method for new code (adapted from `etlhub/CLAUDE.MD`, proposed)

- Work with the **ponytail** skill (root `CLAUDE.md`): native HTML/CSS before a component or a dependency (`BaseDialog` is a native `<dialog>`), reuse `src/config`, services and composables before adding one; mark deliberate shortcuts with `ponytail:`. Dependencies: yarn only.
- Behaviour and its test ship in the same commit. For a new composable, store action, service call or bug fix, write the failing test first. If you did not, say what you did instead of claiming TDD.
- Test behaviour, not implementation: state after a call, the request sent (endpoint, params vs body, headers), what the user sees. Mock `@/services/api` (or `WebSocket`), never the backend. Templates: `services/__tests__/inputs.spec.ts` (request sent), `composables/__tests__/usePipeline.spec.ts` (service mocked, state + notification + confirmation), `views/Dashboard/__tests__/Dashboard.spec.ts` (what the user sees), `utils/__tests__/preview.spec.ts` (pure functions).
- `router/__tests__/guard.spec.ts` redefines the guard inside the test instead of importing `@/router`: it does not test the real guard. Do not copy that pattern.
- New or changed functions and composables: at most 50 lines and 4 parameters, typed (no new `any`), no empty `catch {}`, no `console.log` (the TS equivalents of `except … pass` and `print(`).
- Coverage: no baseline can be measured (no coverage tool installed). Add tests for what you touch.

## Required checks

- Run `yarn vitest run` before and after any change, and `yarn build` after it.
- Changed a call to an `etlhub` endpoint or a contract field: check the frozen contracts above and `etlhub`'s endpoint table; update `useWebSocketLogger.ts`, `services/pipeline.ts` / `usePipeline.ts`, `etlhub`, and the docs in the same change.
- Sending parameters to an endpoint: check in `etlhub` whether it reads query params or a body, and that the parameter exists.
- No new HTTP call outside `services/`, no new `services` import in a view.
- No secret, token or DHIS2 URL in code, logs or tests.

## Where to look next

- `etlhub/CLAUDE.MD` — backend rules, frozen contracts, gotchas
- `etlhub/docs/ARCHITECTURE.md` — runtime topology, state, pipeline order
- `etlhub/docs/DEVELOPMENT.md` — test and clean-code state, proposed rules
- `etlhub/docs/known-issues.md` — security findings (open endpoints, `DHIS_TOKEN` in clear), doc errors
- `.claude/skills/etlhub/SKILL.md` and `references/reference.md` — job lifecycle, WebSocket sequence, endpoint table
- `.claude/skills/etlhub-practices/` — checklists to follow when an endpoint changes on the backend side
