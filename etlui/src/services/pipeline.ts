import api, { withConfirm } from '@/services/api'
import type {
  Checkpoints, Disease, FetchedImport, ForecastRun, GeeVariable, ImportAvailabilityReport, JournalCycle, JournalEvent, Source
} from '@/types/pipeline'

// GET /pipeline/checkpoints: the whole state of the current cycle, in the current mode.
export async function getCheckpoints(): Promise<Checkpoints> {
  const response = await api.get<Checkpoints>('/pipeline/checkpoints')
  return response.data
}

// GET /import_availability: read only, synchronous (a few seconds of DHIS2 requests), journaled by etlhub.
// Sections still valid in the cycle come back reused; refresh=true makes etlhub ask DHIS2 for all of them.
export async function getImportAvailability(refresh = false): Promise<ImportAvailabilityReport> {
  const response = await api.get<ImportAvailabilityReport>('/import_availability', refresh ? { params: { refresh: true } } : undefined)
  return response.data
}

// POST /<task> (or /forecast/ with {}: etlhub's ForecastParams defaults are the files written by validate_inputs): 202 with a job_id: every job is a Celery job (post_forecast since 2026-11-24, update_key since 2026-11-27).
// The X-Request-ID (a UUID) becomes the request_id etlhub tracks: GET /api/tracking/requests/{requestId} finds this launch.
// No dry_run: DRYRUN = TEST MODE, decided by etlhub from the mode.
export type LaunchedJob = { jobId: string | null; requestId: string }
// body: Import GEE's chosen variables ({gee_variables}), kept on the pass by etlhub once the launch is accepted.
export async function launchJob(task: string, confirm = false, body?: { gee_variables: string[] }): Promise<LaunchedJob> {
  const requestId = crypto.randomUUID()
  const config = { params: withConfirm(confirm)?.params ?? {}, headers: { 'X-Request-ID': requestId } }
  const response =
    task === 'forecast'
      ? await api.post('/forecast/', {}, config)
      : await api.post(`/${task}`, body, config)
  return { jobId: response.data?.job_id ?? null, requestId }
}

// POST /pipeline/runs: opens the forecast run of a couple (one at a time); empties input/ and output/.
export async function openRun(source: Source, disease: Disease, confirm = false): Promise<ForecastRun> {
  const response = await api.post<ForecastRun>('/pipeline/runs', { source, disease }, withConfirm(confirm))
  return response.data
}

// DELETE /pipeline/runs/current: nothing is published, the run's items go back to pending.
export async function abandonRun(): Promise<string> {
  const response = await api.delete<{ abandoned: string }>('/pipeline/runs/current')
  return response.data.abandoned
}

// POST /pipeline/runs/current/approve: approve unlocks post_forecast, reject sends the forecast back.
export async function decideRun(decision: 'approve' | 'reject'): Promise<void> {
  await api.post('/pipeline/runs/current/approve', { decision })
}

// POST /pipeline/runs/current/skip_alerts: temporary, calc_orgunit_alerts has no script yet (501); unlocks approve.
export async function skipAlerts(): Promise<void> {
  await api.post('/pipeline/runs/current/skip_alerts')
}

// GET /pipeline/imports/gee: every GEE variable, whether the pass imports it, and the state of its last import.
export async function getGeeImports(): Promise<GeeVariable[]> {
  const response = await api.get<{ variables: GeeVariable[] }>('/pipeline/imports/gee')
  return response.data.variables
}

// GET /pipeline/imports/fetched: per Pivot import, the data elements fetched in this pass with their value check.
export async function getFetchedImports(): Promise<FetchedImport[]> {
  const response = await api.get<{ imports: FetchedImport[] }>('/pipeline/imports/fetched')
  return response.data.imports
}

// POST /pipeline/imports/approve: approve answers 202 with the job_id of the approve_imports job (Celery since 2026-11-27),
// which posts the chosen elements to DHIS2 (the mode's DRYRUN; [] posts nothing) and unlocks build_analytics (step 1):
// followed like any launch; each element's outcome is read after it in GET /pipeline/imports/fetched (`post`).
// reject answers 200 without job_id (jobId null): the approval back to pending. Again after a success: 409
// confirmation_required, resent with confirm=true.
export async function decideImports(decision: 'approve' | 'reject', elements: string[] = [], confirm = false): Promise<LaunchedJob> {
  const requestId = crypto.randomUUID()
  const config = { params: withConfirm(confirm)?.params ?? {}, headers: { 'X-Request-ID': requestId } }
  const response = await api.post('/pipeline/imports/approve', decision === 'approve' ? { decision, elements } : { decision }, config)
  return { jobId: response.data?.job_id ?? null, requestId }
}

// PUT /pipeline/mode: TEST_MODE, the test passes kept apart (DRYRUN stays the .env's); leaving it pauses the active test pass.
// The user's mode (their session). While the mode left has an active pass, etlhub answers 409 confirmation_required
// with impact.actions ['pause', 'abandon']: resent with the user's choice as pass_action.
export type PassAction = 'pause' | 'abandon'
export async function setMode(testMode: boolean, passAction?: PassAction): Promise<boolean> {
  const response = await api.put<{ test_mode: boolean }>('/pipeline/mode', { test_mode: testMode, pass_action: passAction ?? null })
  return response.data.test_mode
}

// PUT /pipeline/cycle: the month (YYYYMM) the next pass starts on; null = follow the calendar month.
export async function setCycle(cycle: string | null): Promise<void> {
  await api.put('/pipeline/cycle', { cycle })
}

// DELETE /pipeline/lock: frees the lock of a job whose worker died (the lock never expires). etlhub asks the workers
// first: while the job may still run, 409 confirmation_required until confirm=true.
export async function releaseLock(confirm = false): Promise<string | null> {
  const response = await api.delete<{ released: string | null }>('/pipeline/lock', withConfirm(confirm))
  return response.data.released
}

// POST /pipeline/passes/current/pause: stop for now; the pass is resumed from the journal.
export async function pausePass(): Promise<void> {
  await api.post('/pipeline/passes/current/pause')
}

// POST /pipeline/passes: starts a new pass on the target month at once (409 confirmation_required after a complete
// or paused pass of that month: the paused one stays paused). etlhub fixes PARENT_OU, LOG_LEVEL and the DHIS2 URL of
// the login (pass-config.md); the GEE variables are chosen in the Import GEE dialog since 2026-11-24 (gee-import.md).
// DRYRUN is never sent: the mode decides it (DRYRUN = TEST MODE).
export async function startPass(confirm = false): Promise<void> {
  await api.post('/pipeline/passes', {}, withConfirm(confirm))
}

// POST /pipeline/passes/{id}/resume: a paused pass of the current mode becomes active again.
export async function resumePass(passId: string): Promise<void> {
  await api.post(`/pipeline/passes/${passId}/resume`)
}

// POST /pipeline/passes/{id}/abandon: for good; the month can be run again in a new pass.
export async function abandonPass(passId: string): Promise<void> {
  await api.post(`/pipeline/passes/${passId}/abandon`)
}

// GET /pipeline/cycles: months with their passes, newest first.
export async function getCycles(): Promise<JournalCycle[]> {
  const response = await api.get<JournalCycle[]>('/pipeline/cycles')
  return response.data
}

// GET /pipeline/passes/{id}/journal: every change of the pass, with the request that caused it.
export async function getJournal(passId: string): Promise<JournalEvent[]> {
  const response = await api.get<JournalEvent[]>(`/pipeline/passes/${passId}/journal`)
  return response.data
}

// GET /output/archive?folder=: the open run's input/ or output/ as a zip, for a native <a download> (it sends the session cookie).
export type ArchiveFolder = 'input' | 'output'
export const archiveUrl = (folder: ArchiveFolder): string => api.getUri({ url: `/output/archive?folder=${folder}` })

// GET /pipeline/passes/{id}/journal.csv (administrators): for a native <a download>, which sends the session cookie.
export const journalCsvUrl = (passId: string): string => api.getUri({ url: `/pipeline/passes/${passId}/journal.csv` })
