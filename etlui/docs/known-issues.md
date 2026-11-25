# etlui — Known issues

Written on 2026-11-25 from the code (`grep -rn "ponytail:" etlui/src`) and from `etlui/CLAUDE.md` (Gotchas). Scope: etlui only; etlhub's are in `etlhub/docs/known-issues.md`.

Priority scale: **P1** fix next (security or a broken feature), **P2** fix soon (wrong behaviour, data integrity), **P3** when convenient. Nothing here is above P3: none loses data or breaks a feature today.

## 1. Technical debt: deliberate shortcuts (`ponytail:` markers)

| Where | Shortcut | Limit | Upgrade |
|---|---|---|---|
| `composables/usePipeline.ts` (`AddActivity`) | The `addActivity` parameter is a no-op for both callers since 2026-11-25 (Recent Activity reads the pass's journal, `usePassActivity`) | Dead parameter and calls | Drop it, its calls in `act` and their assertions in `usePipeline.spec.ts` |
| `composables/useNotification.ts` (`followJob`) | A network error is retried forever | A dead etlhub never ends the job's toast | Give up after N tries |
| `App.vue` (`TOAST_OPTIONS`) | The toasts take the app's tokens, but the library's icons keep their own colours | `vue3-hot-toast` 0.0.5 passes `iconTheme` wrongly; readable on both themes | Fix upstream, or replace the library's icons |
| `views/TrackerView/TrackerView.vue` | Pages built client-side over the last 500 requests | Older requests are not reachable from Tracking | Server-side paging (offset) |
| `views/Dashboard/components/LevelColumn.vue` | `<div class="forecast-runs"><div class="steps-dialog">` wrappers inside the Steps dialog | `ForecastRuns`' global CSS is namespaced; the dialog's portal leaves that tree | Restyle `ForecastRuns` with Tailwind (tailwind-migration phase 6), then drop the wrappers |
| `utils/attention.ts` (`pointTo`) | Waits for the element at most `frames` animation frames | A target rendered later is not pointed to | A `MutationObserver` |
| `utils/checkSummary.ts` | Reads the wording of the library's import check | Another wording shows the raw text | A structured check from etlhub |

## 2. Unused or duplicated code

- **P3 — Configuration update unused** (since 2026-11-25, Parameters read only): `stores/config.ts` `updateConfig`, `services/config.ts` `configService.update` (`PUT /api/config`) and the `ConfigUpdate` type have no caller. Delete them, or keep them if editing comes back.
- **P3 — Two log viewers**: `views/LogsStreamPage.vue` (WebSocket only) and `views/TrackerView/components/JobLogsPanel.vue` (HTTP, then WebSocket while the job runs) show the same logs in two ways, each with its own `CopyLogsButton`.

## 3. Layering debt

Views importing services (rule: views go through a composable or a store; see `CLAUDE.md`, Gotchas):

- `views/Dashboard/components/ForecastReportModal.vue` calls `api` directly.
- `views/Auth/LoginForm.vue` imports `@/services/auth` (`login`).
- The `RequestLog` type is imported from `@/services/api` in `TrackerView/` and, type only, in `types/pipeline.ts`.

## 4. Tests and tooling

- **P3** — No type-check, linter, formatter or coverage tool (`vue-tsc`, ESLint, Prettier, `@vitest/coverage-*` absent); `vite build` does not type-check.
- **P3** — `router/__tests__/guard.spec.ts` redefines the guard instead of importing `@/router`: it does not test the real guard (`router/__tests__/home-redirect.spec.ts` does).
- **P3** — The app-shell checklist (`docs/decision-design/app-shell/`, §8) has not been ticked against a real etlhub; most features since 2026-10-09 were tested with a mocked API only.
