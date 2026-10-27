import type { Component } from 'vue'
import { Bell, ChartPie, CircleCheck, ClipboardList, Cloud, Download, FlaskConical, Key, Map, Upload, Users, Zap } from '@lucide/vue'
import type { Checkpoints, Disease, PipelineItem, Source, StepName } from '@/types/pipeline'

// How each job looks on its card. Pure display: statuses and rules come from etlhub.
const CARDS: Record<string, { label: string; icon: Component }> = {
  import_gee: { label: 'Import GEE', icon: Download },
  import_pivot_com: { label: 'Import Pivot COM', icon: Users },
  import_pivot_csb: { label: 'Import Pivot CSB', icon: ClipboardList },
  build_analytics: { label: 'Build Analytics', icon: ChartPie },
  update_key: { label: 'Update Key', icon: Key },
  fetch_disease: { label: 'Fetch Disease', icon: FlaskConical },
  fetch_climate: { label: 'Fetch Climate', icon: Cloud },
  fetch_geojson: { label: 'Fetch GeoJSON', icon: Map },
  validate_inputs: { label: 'Validate Inputs', icon: CircleCheck },
  forecast: { label: 'Run Forecast', icon: Zap },
  calc_orgunit_alerts: { label: 'Org Unit Alerts (CSB)', icon: Bell },
  post_forecast: { label: 'Post Forecast', icon: Upload }
}

const STATUS_TEXT = { pending: 'Waiting', running: 'Running…', success: '✓ Done', error: '✗ Failed: relaunch' }

/** The job a checkpoint launches: its name ('CSB/Malaria:forecast' -> 'forecast'). */
export const jobOf = (item: string) => item.split(':').pop()!

/** config.json file expected for each disease (shown next to the upload). */
export const CONFIG_FILES: Record<string, string> = {
  Malaria: 'config_malaria.json',
  Diarrhea: 'config_diarrhea.json',
  Respinf: 'config_respiratory.json'
}

export function step(state: Checkpoints | null, name: StepName) {
  return state?.steps.find(s => s.step === name)
}

/** The open run's external_data item: external_data/fkt for ADJ and COM, external_data/csb for CSB. */
export function openLevel(state: Checkpoints | null) {
  const couple = state?.run?.couple
  return couple ? `external_data/${couple.startsWith('CSB/') ? 'csb' : 'fkt'}` : null
}

/** Card label of a checkpoint, also used for notifications and the activity log. */
export function labelOf(item: string): string {
  const name = jobOf(item)
  return CARDS[name]?.label ?? name
}

// Server local time, shown as is ('2026-10-13T14:02:11' -> '2026-10-13 14:02'); only for a success.
export const lastUpdate = (item: PipelineItem) =>
  item.status === 'success' && item.updated_at ? `Last update: ${item.updated_at.slice(0, 16).replace('T', ' ')}` : undefined

/** ActionCard props for one checkpoint. Disabled when etlhub says it cannot start, or while any job runs. */
export function toCard(item: PipelineItem, state: Checkpoints | null, busy: boolean) {
  const card = CARDS[jobOf(item.item)] ?? { label: labelOf(item.item), icon: Zap }
  return {
    key: item.item,
    ...card,
    subtitle: lastUpdate(item),
    loading: item.status === 'running',
    success: item.status === 'success',
    inactive: busy || !item.launchable || (state?.lock != null && item.status !== 'running'),
    statusText: STATUS_TEXT[item.status],
    statusClass: item.status === 'error' ? 'status-error' : 'status-pending'
  }
}

// --- Step ② (forecast). Pure display: statuses and launchable come from etlhub. ---

export const DISEASE_NAMES: Record<Disease, string> = { Malaria: 'Malaria', Diarrhea: 'Diarrhea', Respinf: 'Respiratory infections' }
export const LEVEL_NAMES: Record<Source, string> = { ADJ: 'Adjusted', COM: 'Community sites', CSB: 'Health Centres' }
export const ITEM_NAMES: Record<string, string> = {
  fetch_disease: 'Disease data',
  fetch_climate: 'Climate data',
  fetch_geojson: 'Area maps',
  validate_inputs: 'Data check',
  forecast: 'Forecast computation',
  calc_orgunit_alerts: 'Alert thresholds (CSB only)',
  approve: 'Your approval',
  post_forecast: 'Publication to PRIDE-C'
}

/** Status of an uploaded input file (config/<disease>, external_data/<level>). */
export const FILE_STATUS: Record<string, string> = { pending: 'to provide', running: 'running…', success: '✓ provided', error: '✗ failed' }

/** What the open run may touch: its items, its disease's config, its level's external_data. */
export function inOpenRun(state: Checkpoints, item: string): boolean {
  const couple = state.run?.couple
  return !!couple && (item.startsWith(`${couple}:`) || item === `config/${couple.split('/')[1]}` || item === openLevel(state))
}

/** The next item etlhub says can start in a step (in step ②, of the open run). */
export function nextItem(state: Checkpoints, name: StepName): PipelineItem | undefined {
  return step(state, name)?.items.find(i =>
    i.launchable && i.status !== 'success' && (name !== 'forecast' || inOpenRun(state, i.item)))
}

const STEP_NAMES: Record<StepName, string> = { data_import: 'Data Import', forecast: 'Forecasts', system_update: 'System Update' }

/** Plain name of any checkpoint: 'COM/Malaria:fetch_climate' -> 'Climate data', 'config/Malaria' -> 'Parameters (config.json)'. */
export function itemName(item: string): string {
  if (item.startsWith('config/')) return 'Parameters (config.json)'
  if (item.startsWith('external_data/')) return 'External data'
  if (item === 'approve_imports') return 'Imports approval'
  return ITEM_NAMES[jobOf(item)] ?? labelOf(item)
}

/**
 * Where the pass stands, for the breadcrumb of the Forecast page: step / (open run /) item. The item is the running one,
 * else the next one etlhub says can start, else the first one not in success (waiting for its prerequisites).
 * Read from etlhub's statuses and `launchable`: nothing is decided here.
 */
export function position(state: Checkpoints): string[] {
  const name = positionStep(state)
  if (!name) return ['Complete']
  const crumbs = [STEP_NAMES[name]]
  if (name === 'forecast') {
    if (!state.run) return [...crumbs, 'No run open']
    const [source, disease] = state.run.couple.split('/') as [Source, Disease]
    crumbs.push(`${DISEASE_NAMES[disease]} (${source})`)
  }
  const current = positionItem(state)?.item
  return current ? [...crumbs, itemName(current.item)] : crumbs
}

const running = (state: Checkpoints) =>
  state.steps.flatMap(s => s.items.map(i => ({ step: s.step, item: i }))).find(r => r.item.status === 'running')
const positionStep = (state: Checkpoints): StepName | null => running(state)?.step ?? state.current_step

/** The item of position(): where its last breadcrumb leads (null: complete, or no run open in step ②). */
export function positionItem(state: Checkpoints): { step: StepName; item: PipelineItem } | null {
  const now = running(state)
  if (now) return now
  const name = positionStep(state)
  if (!name || (name === 'forecast' && !state.run)) return null
  const item = nextItem(state, name) ??
    step(state, name)?.items.find(i => i.status !== 'success' && (name !== 'forecast' || inOpenRun(state, i.item)))
  return item ? { step: name, item } : null
}

/** 'COM/Malaria' -> 'Malaria · Community sites (COM)' */
export function coupleName(couple: string): string {
  const [source, disease] = couple.split('/') as [Source, Disease]
  return `${DISEASE_NAMES[disease]} · ${LEVEL_NAMES[source]} (${source})`
}

// etlhub's refusals users meet, in plain words. Unknown messages pass through.
const PLAIN_ERRORS: [RegExp, string][] = [
  [/one job at a time/i, 'A job is already running.'],
  [/needs (an open forecast run|its forecast run open)|no forecast run is open/i, 'Open a forecast run first.'],
  [/is open: finish or abandon it first/i, 'A forecast run is already open: finish or abandon it first.'],
  [/is paused: resume it from the Journal/i, 'This cycle is paused: resume it from the Journal, or choose another month.'],
  [/does not match the run level/i, 'This file does not match the level of this forecast run.'],
  [/administrators only/i, 'Administrators only.'],
  [/needs .* first/i, 'A previous step must be completed first.']
]

export const plainError = (message: string): string => PLAIN_ERRORS.find(([re]) => re.test(message))?.[1] ?? message
