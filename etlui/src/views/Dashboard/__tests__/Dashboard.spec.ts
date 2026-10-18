import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const getCheckpoints = vi.fn()
const launchJob = vi.fn()
const setMode = vi.fn()
const setCycle = vi.fn()
const decideRun = vi.fn()
const decideImports = vi.fn()
const openRun = vi.fn()
const abandonRun = vi.fn()
const apiGet = vi.fn()
const applyDefaultFile = vi.fn()
vi.mock('@/services/pipeline', () => ({
  getCheckpoints: (...args: unknown[]) => getCheckpoints(...args),
  launchJob: (...args: unknown[]) => launchJob(...args),
  setMode: (...args: unknown[]) => setMode(...args),
  setCycle: (...args: unknown[]) => setCycle(...args),
  decideRun: (...args: unknown[]) => decideRun(...args),
  decideImports: (...args: unknown[]) => decideImports(...args),
  openRun: (...args: unknown[]) => openRun(...args),
  abandonRun: (...args: unknown[]) => abandonRun(...args),
  releaseLock: vi.fn()
}))
vi.mock('@/services/inputs', () => ({
  getInputFiles: vi.fn().mockResolvedValue({}),
  getDefaultFiles: vi.fn().mockResolvedValue({
    'config/Malaria': { filename: 'config_malaria.json', size: 795 },
    'external_data/csb': { filename: 'external_data_csb.csv', size: 875612 }
  }),
  applyDefaultFile: (...args: unknown[]) => applyDefaultFile(...args),
  getDefaultPreview: vi.fn(),
  uploadInputFile: vi.fn(),
  deleteInputFile: vi.fn(),
  getConfigPreview: vi.fn(),
  getExternalDataPreview: vi.fn()
}))
vi.mock('@/services/api', () => ({ default: { get: (...args: unknown[]) => apiGet(...args), getUri: ({ url }: { url: string }) => `http://api${url}` }, errorMessage: (_: unknown, f: string) => f }))
vi.mock('vue3-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn() } }))

import Dashboard from '@/views/Dashboard/Dashboard.vue'
import { useAuthStore } from '@/stores/auth'

const item = (name: string, status = 'pending', launchable = false) => ({ item: name, status, job_id: null, updated_at: null, launchable })

function state(overrides: object = {}) {
  return {
    cycle: '202610', cycle_state: 'open', current_step: 'data_import', run: null, lock: null, dry_run: false,
    steps: [
      { step: 'data_import', done: false, accessible: true, items: [{ ...item('import_gee', 'success', true), updated_at: '2026-10-13T14:02:11' }, item('build_analytics')] },
      { step: 'forecast', done: false, accessible: false, items: [item('config/Malaria')] },
      { step: 'system_update', done: false, accessible: false, items: [item('update_key')] }
    ],
    ...overrides
  }
}

const JOBS = ['fetch_disease', 'fetch_climate', 'fetch_geojson', 'validate_inputs', 'forecast', 'approve', 'post_forecast']

/** Step ② with its 71 items; `items` overrides [status, launchable] by item name. */
function forecastState(couple: string | null, items: Record<string, [string, boolean?]> = {}) {
  const names = ['config/Malaria', 'config/Diarrhea', 'config/Respinf', 'external_data/fkt', 'external_data/csb']
  for (const source of ['ADJ', 'COM', 'CSB']) {
    for (const disease of ['Malaria', 'Diarrhea', 'Respinf']) {
      const jobs = source === 'CSB' ? [...JOBS.slice(0, 5), 'calc_orgunit_alerts', ...JOBS.slice(5)] : JOBS
      names.push(...jobs.map(job => `${source}/${disease}:${job}`))
    }
  }
  return state({
    current_step: 'forecast',
    run: couple && { cycle: '202610', couple, state: 'open', disease_code: 'x', ou_level: '6', alert_name: null, opened_at: 't' },
    steps: [
      { step: 'data_import', done: true, accessible: true, items: [item('import_gee', 'success', true)] },
      { step: 'forecast', done: false, accessible: true, items: names.map(n => item(n, items[n]?.[0] ?? 'pending', items[n]?.[1] ?? false)) },
      { step: 'system_update', done: false, accessible: false, items: [] }
    ]
  })
}

async function mountPage() {
  const wrapper = mount(Dashboard, { attachTo: document.body })
  await flushPromises()
  return wrapper
}

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getCheckpoints.mockResolvedValue(state())
    apiGet.mockResolvedValue({ data: '<p>report</p>' })
  })

  it('shows the test mode before step 1 and switches it on the server', async () => {
    setMode.mockResolvedValue(true)
    const wrapper = await mountPage()

    const html = wrapper.html()
    expect(html.indexOf('mode-toggle')).toBeLessThan(html.indexOf('Data Import'))

    await wrapper.findAll('.mode-btn').find(b => b.text() === 'YES')!.trigger('click')
    await flushPromises()
    expect(setMode).toHaveBeenCalledWith(true, false)
    wrapper.unmount()
  })

  it('shows the cycle in a month input and sends the chosen one to the server', async () => {
    setCycle.mockResolvedValue(undefined)
    const wrapper = await mountPage()

    const input = wrapper.find<HTMLInputElement>('input[type="month"]')
    expect(input.element.value).toBe('2026-10')
    await input.setValue('2026-09')
    await flushPromises()
    await input.setValue('')
    await flushPromises()

    expect(setCycle).toHaveBeenNthCalledWith(1, '202609')
    expect(setCycle).toHaveBeenNthCalledWith(2, null)
    wrapper.unmount()
  })

  it('locks the cycle while a run is open', async () => {
    getCheckpoints.mockResolvedValue(forecastState('COM/Malaria'))
    const wrapper = await mountPage()

    expect(wrapper.find('input[type="month"]').attributes('disabled')).toBeDefined()
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
    expect(gee.text()).toContain('Last update: 2026-10-13 14:02')
    expect(build.text()).not.toContain('Last update')

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

  it('shows the imports approval as a decision, not a job card', async () => {
    getCheckpoints.mockResolvedValue(state({ steps: [
      { step: 'data_import', done: false, accessible: true, items: [item('import_gee', 'success', true), item('approve_imports', 'pending', true), item('build_analytics')] },
      { step: 'forecast', done: false, accessible: false, items: [] },
      { step: 'system_update', done: false, accessible: false, items: [] }
    ] }))
    decideImports.mockResolvedValue(undefined)
    const wrapper = await mountPage()

    expect(wrapper.findAll('.action-card').map(c => c.text()).some(t => t.includes('approve_imports'))).toBe(false)
    await wrapper.findAll('button').find(b => b.text() === 'Approve imports')!.trigger('click')
    await flushPromises()
    expect(decideImports).toHaveBeenCalledWith('approve')
    wrapper.unmount()
  })

  it('shows one card per disease with every item of its 3 runs and launches what etlhub allows', async () => {
    launchJob.mockResolvedValue({ jobId: 'fetch_disease_1', requestId: 'r' })
    const forecast = forecastState('COM/Malaria', {
      'config/Malaria': ['success', true], 'external_data/fkt': ['success', true], 'COM/Malaria:fetch_disease': ['pending', true],
      'COM/Malaria:fetch_geojson': ['success'], 'ADJ/Malaria:post_forecast': ['success']
    })
    forecast.steps[1].items.find(i => i.item === 'COM/Malaria:fetch_geojson')!.updated_at = '2026-10-13T14:02:11'
    getCheckpoints.mockResolvedValue(forecast)
    const wrapper = await mountPage()

    const runs = wrapper.find('.forecast-runs')
    expect(runs.find('.todo').text()).toContain('launch “Disease data” for Malaria · Community sites (COM).')
    expect(runs.findAll('.disease-card')).toHaveLength(3)
    const nav = () => runs.findAll('.disease-nav a').map(a => a.classes().includes('is-active'))
    expect(nav()).toEqual([true, false, false])
    const carousel = runs.find('.carousel').element as HTMLElement
    Object.defineProperty(carousel, 'clientWidth', { value: 800 })
    carousel.scrollLeft = 1600
    await runs.find('.carousel').trigger('scroll')
    expect(nav()).toEqual([false, false, true])
    const malaria = runs.find('#forecast-Malaria')
    expect(malaria.text()).toContain('1 of 3 levels published')
    // Only the open run has steps to show: its whole card opens them, highlighted.
    expect(malaria.findAll('.dropzone').every(d => d.element.closest('dialog.steps-dialog'))).toBe(true)
    const [adj, com, csb] = malaria.findAll('.level-column')
    expect(malaria.findAll('button').some(b => b.text() === 'Steps')).toBe(false)
    expect([adj, com, csb].map(l => l.classes().includes('is-open'))).toEqual([false, true, false])
    expect([adj, com, csb].map(l => l.find('.card-steps').exists())).toEqual([false, true, false])
    expect([adj, csb].map(l => l.find('dialog').exists())).toEqual([false, false])
    await com.find('.card-steps').trigger('click')
    expect(com.find('dialog .steps-close').attributes('aria-label')).toBe('Close the steps')
    expect(com.find('dialog').findAll('button').some(b => b.text() === 'Close')).toBe(false)
    // The run's input files first, then its jobs.
    const inputs = com.findAll('.item').filter(i => i.find('.dropzone').exists())
    expect(inputs.map(i => i.find('.item-tech').text())).toEqual(['config/Malaria', 'external_data/fkt'])
    expect(inputs[0].text()).toContain('config_malaria.json')
    expect(inputs[0].text()).toContain('✓ provided · same file for the 3 Malaria runs')
    expect(inputs.map(i => i.find('.dropzone').classes().includes('is-disabled'))).toEqual([false, false])
    // The repo's defaults: offered under each input.
    const useDefault = (input: typeof inputs[0]) => input.findAll('.default-status button').find(b => b.text() === 'Use default')
    expect(inputs[0].find('.default-status').text()).toContain('config_malaria.json')
    expect(inputs[1].find('.default-status').exists()).toBe(false) // no default for fkt in this mock
    applyDefaultFile.mockResolvedValue('input/config.json')
    await useDefault(inputs[0])!.trigger('click')
    await flushPromises()
    expect(applyDefaultFile).toHaveBeenCalledWith('config', false)
    expect(adj.text()).toContain('Published')
    expect(com.findAll('.item')).toHaveLength(8) // 2 input files + 6 jobs: the data check is a button
    // Stage 1 until the data check succeeds: its button waits for the 5 items, stage 2 is locked.
    const tiles = com.findAll('.steps-tile')
    expect(tiles.map(t => t.isVisible())).toEqual([true, false])
    expect(tiles[0].findAll('.item-tech').map(t => t.text())).toEqual(
      ['config/Malaria', 'external_data/fkt', 'fetch_disease', 'fetch_climate', 'fetch_geojson'])
    expect(tiles[1].findAll('.item-tech').map(t => t.text())).toEqual(['forecast', 'approve', 'post_forecast'])
    expect(tiles[0].find('.data-check').text()).toContain('Available once the 5 items above are done')
    expect(tiles[0].findAll('.data-check button').map(b => [b.text(), b.attributes('disabled') !== undefined]))
      .toEqual([['Run the data check', true], ['Next →', true]])
    expect(com.text()).toContain('Disease data')
    expect(com.text()).toContain('fetch_disease')
    expect(com.findAll('.item-time').map(t => t.text())).toEqual(['Last update: 2026-10-13 14:02']) // a success only
    expect(csb.text()).toContain('Available once the open run is done')

    expect(adj.find('progress').attributes()).toMatchObject({ value: '3', max: '9' }) // both shared files are provided
    expect(com.find('dialog').text()).toContain('Disease data')
    const launchButtons = com.findAll('button').filter(b => b.text() === 'Launch')
    expect(launchButtons).toHaveLength(1) // only what etlhub marks launchable
    await launchButtons[0].trigger('click')
    await flushPromises()
    expect(launchJob).toHaveBeenCalledWith('fetch_disease', false)
    wrapper.unmount()
  })

  it('reads the report of the run awaiting approval, then approves it', async () => {
    decideRun.mockResolvedValue(undefined)
    getCheckpoints.mockResolvedValue(forecastState('COM/Malaria', {
      'COM/Malaria:validate_inputs': ['success', true], 'COM/Malaria:approve': ['pending', true]
    }))
    const wrapper = await mountPage()

    expect(wrapper.find('.todo').text()).toContain('approve Malaria · Community sites (COM).')
    const com = wrapper.find('#forecast-Malaria').findAll('.level-column')[1]
    expect(com.text()).toContain('To approve')
    await com.find('.card-steps').trigger('click')
    // The data check succeeded: the dialog shows stage 2, and stage 1 stays reachable to relaunch it.
    expect(com.findAll('.steps-tile').map(t => t.isVisible())).toEqual([false, true])
    expect(com.find('.data-check button').text()).toBe('Relaunch the data check')
    expect(com.text()).toContain('Waiting for your decision')
    await com.find('.tile-nav button').trigger('click') // ← Previous
    expect(com.findAll('.steps-tile').map(t => t.isVisible())).toEqual([true, false])
    // Next: active once the data check succeeded, back to stage 2.
    const next = com.findAll('.data-check button').find(b => b.text() === 'Next →')!
    expect(next.attributes('disabled')).toBeUndefined()
    await next.trigger('click')
    expect(com.findAll('.steps-tile').map(t => t.isVisible())).toEqual([false, true])
    // Read and approve: on the card, and on the approval item of the dialog.
    const approveItem = com.find('dialog .job-approve')
    expect(approveItem.find('button').text()).toBe('Read and approve')
    await approveItem.find('button').trigger('click')
    await flushPromises()
    expect(apiGet).toHaveBeenLastCalledWith('/output/forecast_report.html', { responseType: 'text' })

    await wrapper.findAll('button').find(b => b.text() === 'Approve')!.trigger('click')
    await flushPromises()
    expect(decideRun).toHaveBeenCalledWith('approve')
    wrapper.unmount()
  })

  it('opens a run when none is open, and shows the report kept for a published run', async () => {
    openRun.mockResolvedValue({})
    getCheckpoints.mockResolvedValue(forecastState(null, { 'ADJ/Malaria:post_forecast': ['success'] }))
    const wrapper = await mountPage()

    const [adj, com] = wrapper.find('#forecast-Malaria').findAll('.level-column')
    expect(adj.find('.card-steps').exists()).toBe(false) // no open run: no steps to show
    await com.findAll('button').find(b => b.text() === 'Open')!.trigger('click')
    await flushPromises()
    expect(openRun).toHaveBeenCalledWith('COM', 'Malaria', false)

    await adj.findAll('button').find(b => b.text() === 'View report')!.trigger('click')
    await flushPromises()
    expect(apiGet).toHaveBeenLastCalledWith('/pipeline/runs/ADJ/Malaria/report', { responseType: 'text' })
    wrapper.unmount()
  })

  it('shows the administration zone to administrators only', async () => {
    abandonRun.mockResolvedValue('COM/Malaria')
    getCheckpoints.mockResolvedValue(forecastState('COM/Malaria'))
    let wrapper = await mountPage()
    expect(wrapper.find('.admin-zone').exists()).toBe(false)
    wrapper.unmount()

    useAuthStore().setUser({ id: 'u1', email: null, username: 'admin', displayName: 'Admin', is_admin: true })
    wrapper = await mountPage()
    await wrapper.find('.admin-zone').findAll('button').find(b => b.text() === 'Abandon the open forecast run')!.trigger('click')
    await flushPromises()
    expect(abandonRun).toHaveBeenCalled()
    wrapper.unmount()
  })
})
