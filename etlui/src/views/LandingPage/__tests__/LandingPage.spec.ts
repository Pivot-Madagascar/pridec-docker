import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const getCheckpoints = vi.fn()
const launchJob = vi.fn()
const setMode = vi.fn()
const decideRun = vi.fn()
vi.mock('@/services/pipeline', () => ({
  getCheckpoints: (...args: unknown[]) => getCheckpoints(...args),
  launchJob: (...args: unknown[]) => launchJob(...args),
  setMode: (...args: unknown[]) => setMode(...args),
  decideRun: (...args: unknown[]) => decideRun(...args),
  openRun: vi.fn(),
  abandonRun: vi.fn(),
  releaseLock: vi.fn()
}))
vi.mock('@/services/inputs', () => ({
  getInputFiles: vi.fn().mockResolvedValue({}),
  uploadInputFile: vi.fn(),
  deleteInputFile: vi.fn(),
  getConfigPreview: vi.fn(),
  getExternalDataPreview: vi.fn()
}))
vi.mock('@/services/api', () => ({ default: { get: vi.fn().mockResolvedValue({ data: '' }) } }))
vi.mock('vue3-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn() } }))

import LandingPage from '@/views/LandingPage/LandingPage.vue'

const item = (name: string, status = 'pending', launchable = false) => ({ item: name, status, job_id: null, updated_at: null, launchable })

function state(overrides: object = {}) {
  return {
    cycle: '202610', cycle_state: 'open', current_step: 'data_import', run: null, lock: null, dry_run: false,
    steps: [
      { step: 'data_import', done: false, accessible: true, items: [item('import_gee', 'success', true), item('build_analytics')] },
      { step: 'forecast', done: false, accessible: false, items: [item('config/Malaria')] },
      { step: 'system_update', done: false, accessible: false, items: [item('update_key')] }
    ],
    ...overrides
  }
}

const OPEN_RUN = {
  current_step: 'forecast',
  run: { cycle: '202610', couple: 'COM/Malaria', state: 'open', disease_code: 'pridec_historic_COMMalaria', ou_level: '6',
         alert_name: null, external_data: 'none', opened_at: 't' },
  steps: [
    { step: 'data_import', done: true, accessible: true, items: [item('import_gee', 'success', true)] },
    { step: 'forecast', done: false, accessible: true, items: [
      item('config/Malaria', 'success', true), item('COM/Malaria:fetch_disease', 'pending', true),
      item('COM/Malaria:forecast'), item('COM/Malaria:approve'), item('ADJ/Malaria:fetch_disease')
    ] },
    { step: 'system_update', done: false, accessible: false, items: [] }
  ]
}

async function mountPage() {
  const wrapper = mount(LandingPage, { attachTo: document.body })
  await flushPromises()
  return wrapper
}

describe('LandingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getCheckpoints.mockResolvedValue(state())
  })

  it('shows the test mode before step 1 and switches it on the server', async () => {
    setMode.mockResolvedValue(true)
    const wrapper = await mountPage()

    const html = wrapper.html()
    expect(html.indexOf('mode-toggle')).toBeLessThan(html.indexOf('① Data Import'))

    await wrapper.findAll('.mode-btn').find(b => b.text() === 'OUI')!.trigger('click')
    await flushPromises()
    expect(setMode).toHaveBeenCalledWith(true, false)
    wrapper.unmount()
  })

  it('enables only the cards etlhub says are launchable', async () => {
    launchJob.mockResolvedValue('job')
    const wrapper = await mountPage()

    const cards = wrapper.findAll('.action-card')
    const gee = cards.find(c => c.text().includes('Import GEE'))!
    const build = cards.find(c => c.text().includes('Build Analytics'))!
    expect(gee.attributes('disabled')).toBeUndefined()
    expect(build.attributes('disabled')).toBeDefined()
    expect(gee.text()).toContain('✓ Done')

    await gee.trigger('click')
    await flushPromises()
    expect(launchJob).toHaveBeenCalledWith('import_gee', false)
    wrapper.unmount()
  })

  it('asks for the approval checkbox before resending with confirm=true', async () => {
    launchJob
      .mockRejectedValueOnce({ response: { status: 409, data: { code: 'confirmation_required', message: 'import_gee is already in success',
        impact: { item: 'import_gee', step: 'data_import', reset_items: [], blocked_steps: ['forecast', 'system_update'] } } } })
      .mockResolvedValueOnce('job_2')
    const wrapper = await mountPage()

    await wrapper.findAll('.action-card').find(c => c.text().includes('Import GEE'))!.trigger('click')
    await flushPromises()
    const dialog = wrapper.find('.impact-dialog')
    expect(dialog.text()).toContain('forecast, system_update')
    const confirmButton = dialog.findAll('button').find(b => b.text() === 'Confirm')!
    expect(confirmButton.attributes('disabled')).toBeDefined()

    await dialog.find('input[type="checkbox"]').setValue(true)
    await confirmButton.trigger('click')
    await flushPromises()
    expect(launchJob).toHaveBeenLastCalledWith('import_gee', true)
    wrapper.unmount()
  })

  it('shows the open run with its own jobs only, and approval waiting for the forecast', async () => {
    getCheckpoints.mockResolvedValue(state(OPEN_RUN))
    const wrapper = await mountPage()

    const runs = wrapper.find('.forecast-runs')
    expect(runs.text()).toContain('Run COM/Malaria')
    expect(runs.text()).toContain('pridec_historic_COMMalaria')
    const runCards = runs.findAll('.action-card').map(c => c.text())
    expect(runCards.some(t => t.includes('Fetch Disease'))).toBe(true)
    expect(runCards).toHaveLength(2) // fetch_disease and forecast of COM/Malaria; not ADJ/Malaria, not approve
    const approve = runs.findAll('button').find(b => b.text() === 'Approve')!
    expect(approve.attributes('disabled')).toBeDefined()
    wrapper.unmount()
  })
})
