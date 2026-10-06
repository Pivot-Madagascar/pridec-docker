# etlui

## Purpose

Vue 3 + TypeScript front-end (Vite 7, Pinia 3, vue-router 4, axios, Tailwind 4, `vue3-hot-toast`) that drives the PRIDE-C pipeline. It calls the REST API of `etlhub` (port 8111) and follows jobs over its log WebSocket. It has no backend of its own: in production it is static files served by nginx.

## Module map

- `src/composables/` — `useEtlPipeline.ts` (launches the ETL, fetch, validation and report endpoints; holds loading/success state), `useWebSocketLogger.ts` (log WebSocket client), `useNotification.ts` (toasts through `vue3-hot-toast`), `useActivityLog.ts` (recent activity list), `useInputUpload.ts` (upload, server state and deletion of `input/config.json` + `input/external_data.csv`), `useInputPreview.ts` (preview of those files, from the server or from the selected `File`)
- `src/stores/` (Pinia) — `auth.ts` (DHIS2 token and user, persisted in `localStorage`), `config.ts` (dynamic config through `configService`), `forecastConfig.ts` (disease, data source, test mode → `diseaseCode`, `ouLevel`, `alertName`, `forecastStart`), `useTrackingStore.ts` (request tracking, 2 s polling)
- `src/services/` — `api.ts` (axios instance + `Authorization: Bearer` interceptor + 401 → `/login`, `trackingApi`, `RequestLog` / `ServiceCallLog` types), `auth.ts` (`handleTokenSubmit` through `fetch` to `/auth/validate-token`, `logout`), `config.ts` (`configService` for `/api/config`), `inputs.ts` (`uploadInputFile` → multipart `POST /input/files/{name}`, `getInputFiles` → `GET /input/files`, `deleteInputFile` → `DELETE /input/files/{name}`, `getConfigPreview`, `getExternalDataPreview` → `GET /input/files/*/preview`)
- `src/views/` — `LandingPage/` (dashboard; `components/` holds the pipeline UI — `Accordion`, `ETLPipeline`, `StepperCarousel`, `ActionCard`, `QuickActions`, `HeroSection`, `RecentActivity`, `Notifications` —, the forecast UI — `ForecastConfigForm`, `ForecastModal`, `ForecastReportModal` — and the input-file UI — `FileDropzone`, `PreviewDialog`, `ConfigPreview`, `CsvPreview`, `ConfirmDialog`), `TrackerView/` (request tracking, `RequestTable`, `RequestDetail`), `LogsStreamPage.vue` (live logs), `JobStatus.vue` (`/status/:jobId`), `Auth/` (`LoginForm`, `ParametersPage`), `Admin/ConfigView.vue`
- `src/router/index.ts` — routes + global guard (`meta.public`, redirect to `Login`)
- `src/types/` — `config.ts` (`ConfigResponse`), `etl.ts` (`ActivityEntry`), `inputs.ts` (`InputName`, `ServerFile`, `CsvPreviewData`, `ConfigData`)
- `src/config/data.ts` — static definitions of the dashboard actions and steps (keys = endpoint names)
- `src/utils/preview.ts` — pure helpers, no I/O: streaming CSV parser (`createCsvParser`, `previewCsvStream`, same output shape as etlhub's preview), `formatPeriod`, `formatCell`
- `src/components/` — `Drawer.vue`, `Icons/` (inline SVG paths, `Icon` + `ICONS`). `src/styles/base.css`.
- Tests: `__tests__/*.spec.ts` next to the code (`router/`, `services/`, `composables/`, `utils/`). `vitest.config.ts`: `happy-dom`, `globals: true`, `src/test/setup.ts` (fresh Pinia before each test).

Siblings in the repo:
- `etlhub/` is the only backend. Endpoint table: `.claude/skills/etlhub/references/reference.md`.
- `etl/` and `forecast/` are never called directly: always through `etlhub`.

## Rules

- **The `etlhub` contracts are frozen** (copied from `etlhub/CLAUDE.MD`): `ETLResponse` = `{status, message, job_id, webhook_url}`. `JobStatus` = `{status, job_id, started, completed, logs, message}`. `job_id` = `<task_type>_<uuid4 hex[:8]>`. WebSocket messages: `etl_log_history`, `job_status_update`, `etl_log_entry`, `etl_log_complete`, close code `4004`. Any change must be mirrored in `etlui/src/composables/useWebSocketLogger.ts` and `useEtlPipeline.ts` in the same change, and on the `etlhub` side too. Never change a contract on one side only.
- **Never trigger real jobs against a real DHIS2 or the host** from the dev UI without explicit approval. The dashboard buttons call `/import_*`, `/build_analytics`, `/calc_csb_alerts`, `/post_forecast`, `/update_key` (write to DHIS2), `/forecast/` (`docker run`), `DELETE /output/reset` (`rm -rf output/`) and `POST` / `DELETE /input/files/{name}` (overwrite or delete files in `input/`). Use an `etlhub` running with `DRYRUN=true`. Tests mock `@/services/api` (or the service module), never a real backend.
- **Layering**: `views` → `composables` / `stores` → `services` → `types`. `router` only reads `stores/auth`. HTTP calls (`axios`, `fetch`) live in `services/` only. The WebSocket lives in `useWebSocketLogger.ts` only. Views do not import `@/services/*`; they go through a composable or a store. Existing violations are known debt (see Gotchas): do not add new ones, do not refactor them unless asked.
- **Composables orchestrate, they hold no business rules.** Domain rules (disease code, OU level per data source, alert names, forecast start) stay in `stores/forecastConfig.ts`. A composable calls a service, updates state, notifies. Follow `useInputUpload.ts` / `useInputPreview.ts` (service calls only, state per call, typed) rather than `useEtlPipeline.ts`.
- **No long blocking `await`.** A launch endpoint returns 202 with a `job_id`. Never wait for a job to finish inside a click handler: follow it through the WebSocket or a polling loop that stops on `success` / `error`.
- **Never print or copy secrets.** Do not log the token, `DHIS_TOKEN` or the `Authorization` header. Mention variable names only (`VITE_API_BASE_URL`, `VITE_DHIS2_URL`).
- **Never hardcode a DHIS2 URL or the API URL.** Use `import.meta.env.VITE_*`. The only allowed literal is the existing `http://localhost:8111` fallback; do not add new copies of it (there are already four: `services/api.ts`, `services/auth.ts`, `App.vue`, `LogsStreamPage.vue`).

## Gotchas

- `useEtlPipeline` sends a JSON body to `/fetch_disease` (`disease_code`, `ou_level`) and `/validate_inputs` (the whole forecast config store), but `etlhub` reads **query parameters only**, and neither endpoint has those parameters anyway (`/fetch_disease` takes `webhook_url`; `/validate_inputs` takes file paths, `input_dir`, `webhook_url`). The body is silently ignored.
- **WebSocket `4004`**: `etlhub` accepts the socket, then closes with `4004` when no log exists yet (right after the 202, and during a whole forecast run since forecast logs are written at the end). It is a clean close, so `useWebSocketLogger` does **not** retry (it only retries `!event.wasClean`, max 5, while status is not `success` / `error`). Nothing is shown to the user either: `4004` is not handled explicitly. Read from the code, not tested in a browser.
- `useWebSocketLogger` builds the URL with `baseUrl.replace(/^https?/, 'ws')`: an `https://` base becomes `ws://`, not `wss://`. With `baseUrl = ''` the URL is relative.
- `GET /api/config/` returns `DHIS_TOKEN` in clear and `ConfigView.vue` shows it. The raw DHIS2 token is also stored in `localStorage` (`token`). The log WebSocket sends no token. Only `/api/config/*` and `/auth/me` are protected on the backend.
- `useEtlPipeline` state (`loading`, `results`, `lastJobId`, `*Success`…) is **module-level**: shared by every caller and kept across route changes. `resetReports` uses the native `window.confirm`, not `ConfirmDialog.vue`.
- `JobStatus.vue` uses `/forecast/status/{job_id}` for every job. `pollStatus()` checks `status` before the first `checkStatus()` resolves, so the 3 s polling never starts. Its stop condition also misses `error`. It compares against `completed` / `failed`, which `etlhub` does not send (`running`, `success`, `error`).
- `services/api.ts` defaults `baseURL` to the absolute `http://localhost:8111`, so the Vite proxy (`/api`, `/auth` → `:8111`) is bypassed in dev and `etlhub` must allow CORS (it does, `api/middleware.py`). Most endpoints (`/import_*`, `/fetch_*`, `/forecast`, `/output`, `/input`) are not in the proxy anyway.
- `vite.config.ts` sets `envDir: '../../'`, i.e. the **parent of the repo**, not the repo root. The root `.env` defines `VITE_*` variables, but Vite does not read them from there (read from the config, not executed).
- Ports: Vite dev uses its default (5173, no `port` set). nginx listens on **8000**, but the `Dockerfile` says `EXPOSE 8111` (the API port). The `etlui` service is commented out in `compose.yaml`.
- A 401 from any axios call clears the store and does a hard `window.location.href = '/login'`.
- The drawer (`App.vue` `navItems`) links to `/forecast`, which has no route.
- Toasts: `useNotification` calls `vue3-hot-toast` directly. `LandingPage` also passes its `notification` ref to `Notifications.vue` (which would toast again on change), but never calls its own `showNotification`, so that component never fires. Each `useNotification()` call has its own refs.
- `ActivityEntry` is defined twice (`types/etl.ts` and `useEtlPipeline.ts`). There is no TS type for `ETLResponse` or `JobStatus`: responses are read untyped (`response.data?.job_id`).
- Views importing services (layering debt): `api` called directly in `JobStatus.vue`, `LandingPage/components/ForecastModal.vue`, `LandingPage/components/ForecastReportModal.vue`; `@/services/auth` in `Auth/LoginForm.vue` (`handleTokenSubmit`) and `Auth/ParametersPage.vue` (`logout`); `RequestLog` type imported from `@/services/api` in `TrackerView/`.
- `apiFetch` in `services/auth.ts` is unused. `lucide-vue-next` is a dependency but is imported nowhere (icons are inline SVG in `components/Icons/`).
- `useActivityLog()` creates a new list on every call: entries added by `useEtlPipeline` never reach the list `LandingPage` shows. `useInputUpload` takes the page's `addActivity` as a parameter instead.
- The `api` instance defaults to `Content-Type: application/json`, which makes axios serialize a `FormData` as JSON. Pass `multipart/form-data` explicitly for uploads (see `services/inputs.ts`).

## Commands

Run from `etlui/`. `npm` is the reference (`Dockerfile` runs `npm ci`); a `yarn.lock` also exists, do not update both.

- Install: `npm ci`
- Dev: `npm run dev` (Vite; needs `etlhub` on `:8111`, proxy `/api` and `/auth`)
- Build: `npm run build` (output `dist/`, git-ignored). `vite build` does **not** type-check.
- Preview: `npm run preview`
- Tests: `npx vitest run` (there is no `test` script). 5 files, 36 tests, all passing.
- One file: `npx vitest run src/composables/__tests__/useInputUpload.spec.ts`
- Type-check, linter, formatter, coverage: none installed (`vue-tsc`, ESLint, Prettier and `@vitest/coverage-*` are absent). Do not invent one.
- Docker: `docker build -t etlui etlui/` → nginx on 8000.

## Method for new code (adapted from `etlhub/CLAUDE.MD`, proposed)

- Behaviour and its test ship in the same commit. For a new composable, store action, service call or bug fix, write the failing test first. If you did not, say what you did instead of claiming TDD.
- Test behaviour, not implementation: state after a call, the request sent (endpoint, params vs body, headers), what the user sees. Mock `@/services/api` (or `WebSocket`), never the backend. Templates: `services/__tests__/inputs.spec.ts` (request sent), `composables/__tests__/useInputUpload.spec.ts` (service mocked, state + notification), `utils/__tests__/preview.spec.ts` (pure functions).
- `router/__tests__/guard.spec.ts` redefines the guard inside the test instead of importing `@/router`: it does not test the real guard. Do not copy that pattern.
- New or changed functions and composables: at most 50 lines and 4 parameters, typed (no new `any`), no empty `catch {}`, no `console.log` (the TS equivalents of `except … pass` and `print(`).
- Coverage: no baseline can be measured (no coverage tool installed). Add tests for what you touch.

## Required checks

- Run `npx vitest run` before and after any change, and `npm run build` after it.
- Changed a call to an `etlhub` endpoint or a contract field: check the frozen contracts above and `etlhub`'s endpoint table; update `useWebSocketLogger.ts` and `useEtlPipeline.ts`, `etlhub`, and the docs in the same change.
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
