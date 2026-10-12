import { ICONS } from '@/components/Icons'
import type { Checkpoints, PipelineItem, StepName } from '@/types/pipeline'

// How each job looks on its card. Pure display: statuses and rules come from etlhub.
const CARDS: Record<string, { label: string; icon: string; iconClass: string }> = {
  import_gee: { label: 'Import GEE', icon: ICONS.download, iconClass: 'icon-blue' },
  import_pivot_com: { label: 'Import Pivot COM', icon: ICONS.users, iconClass: 'icon-green' },
  import_pivot_csb: { label: 'Import Pivot CSB', icon: ICONS.clipboardList, iconClass: 'icon-purple' },
  build_analytics: { label: 'Build Analytics', icon: ICONS.chartPie, iconClass: 'icon-emerald' },
  update_key: { label: 'Update Key', icon: ICONS.key, iconClass: 'icon-slate' },
  fetch_disease: { label: 'Fetch Disease', icon: ICONS.beaker, iconClass: 'icon-teal' },
  fetch_climate: { label: 'Fetch Climate', icon: ICONS.cloud, iconClass: 'icon-sky' },
  fetch_geojson: { label: 'Fetch GeoJSON', icon: ICONS.map, iconClass: 'icon-indigo' },
  validate_inputs: { label: 'Validate Inputs', icon: ICONS.checkCircle, iconClass: 'icon-teal' },
  forecast: { label: 'Run Forecast', icon: ICONS.lightning, iconClass: 'icon-orange' },
  calc_orgunit_alerts: { label: 'Org Unit Alerts (CSB)', icon: ICONS.bell, iconClass: 'icon-amber' },
  post_forecast: { label: 'Post Forecast', icon: ICONS.upload, iconClass: 'icon-rose' }
}

const STATUS_TEXT = { pending: 'Waiting', running: 'Running…', success: '✓ Done', error: '✗ Failed: relaunch' }

/** 'CSB/Malaria:forecast' -> 'forecast' */
const nameOf = (item: string) => item.split(':').pop()!

/** The job a checkpoint launches: its name ('CSB/Malaria:forecast' -> 'forecast'). */
export const jobOf = nameOf

/** config.json file expected for each disease (shown next to the upload). */
export const CONFIG_FILES: Record<string, string> = {
  Malaria: 'config_malaria.json',
  Diarrhea: 'config_diarrhea.json',
  Respinf: 'config_respiratory.json'
}

export function step(state: Checkpoints | null, name: StepName) {
  return state?.steps.find(s => s.step === name)
}

/** Card label of a checkpoint, also used for notifications and the activity log. */
export function labelOf(item: string): string {
  const name = nameOf(item)
  return CARDS[name]?.label ?? name
}

/** ActionCard props for one checkpoint. Disabled when etlhub says it cannot start, or while any job runs. */
export function toCard(item: PipelineItem, state: Checkpoints | null, busy: boolean) {
  const card = CARDS[nameOf(item.item)] ?? { label: labelOf(item.item), icon: ICONS.lightning, iconClass: 'icon-slate' }
  return {
    key: item.item,
    ...card,
    loading: item.status === 'running',
    success: item.status === 'success',
    inactive: busy || !item.launchable || (state?.lock != null && item.status !== 'running'),
    statusText: STATUS_TEXT[item.status],
    statusClass: item.status === 'error' ? 'status-error' : 'status-pending',
    loadingText: 'Running…',
    successText: '✓ Done'
  }
}
