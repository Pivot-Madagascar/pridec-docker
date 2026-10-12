import api, { withConfirm } from '@/services/api'
import type { Checkpoints, Disease, ForecastRun, Source } from '@/types/pipeline'

// GET /pipeline/checkpoints: the whole state of the current cycle, in the current mode.
export async function getCheckpoints(): Promise<Checkpoints> {
  const response = await api.get<Checkpoints>('/pipeline/checkpoints')
  return response.data
}

// POST /<task> (or /forecast/ with {}: etlhub's ForecastParams defaults are the files written by validate_inputs): 202 with a job_id for Celery jobs, 200 for post_forecast and update_key.
export async function launchJob(task: string, confirm = false): Promise<string | null> {
  const response =
    task === 'forecast'
      ? await api.post('/forecast/', {}, withConfirm(confirm))
      : await api.post(`/${task}`, undefined, withConfirm(confirm))
  return response.data?.job_id ?? null
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

// PUT /pipeline/mode: test mode = DRYRUN=true; leaving it discards the test checkpoints (confirm when there are any).
export async function setMode(dryRun: boolean, confirm = false): Promise<boolean> {
  const response = await api.put<{ dry_run: boolean }>('/pipeline/mode', { dry_run: dryRun }, withConfirm(confirm))
  return response.data.dry_run
}

// DELETE /pipeline/lock: frees the lock of a job whose worker died (the lock never expires).
export async function releaseLock(): Promise<string | null> {
  const response = await api.delete<{ released: string | null }>('/pipeline/lock')
  return response.data.released
}
