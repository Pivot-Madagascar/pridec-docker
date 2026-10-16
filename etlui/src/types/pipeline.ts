// Shapes returned by etlhub's /pipeline routes (etlhub/docs/decision-design/pipeline-checkpoints/pipeline-checkpoints.md).

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
  cycle: string
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

export interface Checkpoints {
  cycle: string
  cycle_state: 'open' | 'closed'
  current_step: StepName | null
  run: ForecastRun | null
  lock: PipelineLock | null
  dry_run: boolean
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
