import api, { withConfirm } from '@/services/api'
import type { Checkpoints, Disease, ForecastRun, Source } from '@/types/pipeline'

// GET /pipeline/checkpoints: the whole state of the current cycle, in the current mode.
export async function getCheckpoints(): Promise<Checkpoints> {
  const response = await api.get<Checkpoints>('/pipeline/checkpoints')
  return response.data
}

// POST /<task> (or /forecast/ with {}: etlhub's ForecastParams defaults are the files written by validate_inputs): 202 with a job_id for Celery jobs, 200 for post_forecast and update_key.
// The X-Request-ID (a UUID) becomes the request_id etlhub tracks: GET /api/tracking/requests/{requestId} finds this launch.
export type LaunchedJob = { jobId: string | null; requestId: string }
export async function launchJob(task: string, confirm = false): Promise<LaunchedJob> {
  const requestId = crypto.randomUUID()
  const config = { ...withConfirm(confirm), headers: { 'X-Request-ID': requestId } }
  const response =
    task === 'forecast'
      ? await api.post('/forecast/', {}, config)
      : await api.post(`/${task}`, undefined, config)
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

// POST /pipeline/imports/approve: approve unlocks build_analytics (step 1), reject sends the approval back to pending.
export async function decideImports(decision: 'approve' | 'reject'): Promise<void> {
  await api.post('/pipeline/imports/approve', { decision })
}

// PUT /pipeline/mode: test mode = DRYRUN=true; leaving it discards the test checkpoints (confirm when there are any).
export async function setMode(dryRun: boolean, confirm = false): Promise<boolean> {
  const response = await api.put<{ dry_run: boolean }>('/pipeline/mode', { dry_run: dryRun }, withConfirm(confirm))
  return response.data.dry_run
}

// PUT /pipeline/cycle: the cycle (YYYYMM) launches go to; null = follow the calendar month.
export async function setCycle(cycle: string | null): Promise<void> {
  await api.put('/pipeline/cycle', { cycle })
}

// DELETE /pipeline/lock: frees the lock of a job whose worker died (the lock never expires).
export async function releaseLock(): Promise<string | null> {
  const response = await api.delete<{ released: string | null }>('/pipeline/lock')
  return response.data.released
}
