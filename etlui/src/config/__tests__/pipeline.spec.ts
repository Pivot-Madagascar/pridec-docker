import { describe, it, expect } from 'vitest'
import { position, positionItem } from '@/config/pipeline'
import type { Checkpoints, ItemStatus, StepName } from '@/types/pipeline'

const item = (name: string, status: ItemStatus = 'pending', launchable = false) =>
  ({ item: name, status, job_id: null, updated_at: null, launchable })

function state(current: StepName | null, items: Partial<Record<StepName, ReturnType<typeof item>[]>>, couple: string | null = null) {
  return {
    cycle: '202610', current_step: current, lock: null, test_mode: false, dry_run: true, pass: null,
    run: couple && { pass_id: 'p', couple, state: 'open', disease_code: 'x', ou_level: '6', alert_name: null, opened_at: 't' },
    steps: (['data_import', 'forecast', 'system_update'] as StepName[]).map(s => ({ step: s, done: false, accessible: true, items: items[s] ?? [] }))
  } as Checkpoints
}

describe('position (breadcrumb of the Forecast page)', () => {
  it('is the step, then its next item that etlhub says can start', () => {
    const s = state('data_import', { data_import: [item('import_gee', 'success', true), item('import_pivot_com', 'pending', true), item('build_analytics')] })
    expect(position(s)).toEqual(['Data Import', 'Import Pivot COM'])
    expect(positionItem(s)).toMatchObject({ step: 'data_import', item: { item: 'import_pivot_com' } }) // where the link goes
  })

  it('is the running item first, wherever it is', () => {
    const s = state('data_import', { data_import: [item('import_gee', 'running', true), item('import_pivot_com', 'pending', true)] })
    expect(position(s)).toEqual(['Data Import', 'Import GEE'])
  })

  it('in Forecasts: the open run, then its next item (its shared files included)', () => {
    const forecast = [item('config/Malaria', 'success'), item('COM/Malaria:fetch_disease', 'success', true), item('COM/Malaria:fetch_climate', 'pending', true)]
    expect(position(state('forecast', { forecast }, 'COM/Malaria'))).toEqual(['Forecasts', 'Malaria (COM)', 'Climate data'])
    const toUpload = [item('config/Malaria', 'pending', true), item('COM/Malaria:fetch_disease', 'pending', true)]
    expect(position(state('forecast', { forecast: toUpload }, 'COM/Malaria'))).toEqual(['Forecasts', 'Malaria (COM)', 'Parameters (config.json)'])
  })

  it('in Forecasts without an open run, says so; a complete pass is complete', () => {
    expect(position(state('forecast', { forecast: [item('COM/Malaria:fetch_disease')] }))).toEqual(['Forecasts', 'No run open'])
    expect(position(state(null, {}))).toEqual(['Complete'])
  })
})
