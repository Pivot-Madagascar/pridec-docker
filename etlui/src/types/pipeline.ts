// Shapes returned by etlhub's /pipeline routes (etlhub/docs/decision-design/pipeline-checkpoints/pipeline-checkpoints.md).
import type { RequestLog } from '@/services/api' // type only: RequestLog still lives in services (known debt)

export type ItemStatus = 'pending' | 'running' | 'success' | 'error'
export type StepName = 'data_import' | 'forecast' | 'system_update'

export interface PipelineItem {
  item: string // 'import_gee', 'config/Malaria', 'external_data/fkt', 'CSB/Malaria:forecast'…
  status: ItemStatus
  job_id: string | null
  updated_at: string | null
  launchable: boolean // step accessible, prerequisites in success, item of the open run (ignores the lock)
}

export interface PipelineStep {
  step: StepName
  done: boolean
  accessible: boolean
  items: PipelineItem[]
}

export interface ForecastRun {
  pass_id: string
  couple: string // 'CSB/Malaria'
  state: 'open' | 'closed' | 'abandoned'
  disease_code: string
  ou_level: string
  alert_name: string | null
  opened_at: string
}

export interface PipelineLock {
  job_id: string
  task: string
  acquired_at: string
}

// One run of a cycle (etlhub/docs/decision-design/cycle-passes/cycle-passes.md).
export type PassState = 'active' | 'paused' | 'complete' | 'abandoned'
export interface Pass {
  id: string // 8 hex characters
  cycle: string // YYYYMM
  state: PassState
  started_at: string
  started_by: string | null // DHIS2 username, 'worker' or 'system'
}

export interface Checkpoints {
  cycle: string
  pass: Pass | null // the active pass, else the last one of the target month; null before its first launch
  current_step: StepName | null
  run: ForecastRun | null
  lock: PipelineLock | null
  test_mode: boolean // TEST_MODE: where the pipeline state lives, switched by PUT /pipeline/mode
  dry_run: boolean // DRYRUN of the root .env, read only: whether the scripts write to DHIS2
  steps: PipelineStep[]
}

// Body of a 409 that asks the user to confirm before undoing something (rule R5).
export interface ConfirmationRequired {
  code: 'confirmation_required'
  message: string
  impact: Record<string, unknown>
}

export const SOURCES = ['ADJ', 'COM', 'CSB'] as const
export const DISEASES = ['Malaria', 'Diarrhea', 'Respinf'] as const
export type Source = (typeof SOURCES)[number]
export type Disease = (typeof DISEASES)[number]

// GET /pipeline/passes/{pass_id}/journal (etlhub/docs/decision-design/cycle-journal/cycle-journal.md).
export interface JournalEvent {
  cycle: string
  pass_id: string | null
  at: string // local ISO time, microseconds
  step: StepName | null
  item: string | null
  // pass_started, launched, succeeded, failed, reset, uploaded, removed, decided, skipped, run_opened, run_closed,
  // run_abandoned, lock_released, mode_changed, paused, resumed, abandoned, cycle_closed,
  // carried_over (an import or approve_imports done in an earlier pass of the cycle, detail {from_pass, status,
  // updated_at, dry_run?}, job_id = that pass's job), availability_checked / availability_reused (GET /import_availability, detail {checked?, reused?, missing,
  // analytics_behind, errors} or {error})
  event: string
  job_id: string | null
  actor: string | null // DHIS2 username, 'worker' or 'system'
  request_id: string | null
  detail: Record<string, unknown> | null
  mode: 'production' | 'test' // test events: kept in Redis only, while Redis keeps them
  request: RequestLog | null // the HTTP request that caused it, or null
}

// GET /pipeline/cycles: months with passes (and the target one), newest first, each with its passes, newest first.
export interface JournalPass extends Pass {
  mode: 'production' | 'test' // test passes: kept in Redis only
  events: number // mode_changed and availability_checked left out (as last_at)
  last_at: string | null
}
export interface JournalCycle {
  cycle: string // YYYYMM
  target: boolean // launches go to it
  passes: JournalPass[]
}

// GET /import_availability (etl/scripts/check_import_availability.py). Counts: orgUnits with a value, per period (YYYYMM).
export interface ElementAvailability {
  code: string
  raw: Record<string, number> | null // stored values (/api/dataValueSets); null if the query failed
  analytics: Record<string, number> | null // values in the analytics tables; null if the query failed
  last_updated: string | null
  imported: boolean // a stored value for every period
  analytics_up_to_date: boolean | null // analytics == raw; null if a query failed
  error: string | null
}
export interface ImportAvailability {
  task: string // import_gee, import_pivot_com, import_pivot_csb
  periods: string[]
  org_units: string
  elements: ElementAvailability[]
  checked_at: string // when this section's check started, etlhub local time (as the journal)
  checked_by: string | null
  pass_id: string | null // null: checked before the month's first launch
  reused: boolean // checked earlier in the cycle (any pass, any user) and still valid: DHIS2 not asked now
}
export interface ImportAvailabilityReport {
  dhis_url: string
  last_analytics: string | null // DHIS2's last analytics build (server local time), read by the latest section check
  imports: ImportAvailability[]
}
