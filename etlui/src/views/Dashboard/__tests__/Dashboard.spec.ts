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
vi.mock('@/services/api', () => ({ default: { get: (...args: unknown[]) => apiGet(...args) }, errorMessage: (_: unknown, f: string) => f }))
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
    getCheckpoints.mockResolvedValue(forecastState('COM/Malaria', {
      'config/Malaria': ['success', true], 'external_data/fkt': ['success', true], 'COM/Malaria:fetch_disease': ['pending', true],
      'ADJ/Malaria:post_forecast': ['success']
    }))
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
    // One config.json input per disease; only the open run's disease can change it.
    expect(malaria.find('.input-file').text()).toContain('config_malaria.json')
    expect(malaria.find('.dropzone').classes()).not.toContain('is-disabled')
    expect(runs.find('#forecast-Diarrhea .dropzone').classes()).toContain('is-disabled')
    // Two shared external_data.csv inputs in each card; only the open run's level (fkt for COM) is active.
    expect(runs.findAll('.external-data')).toHaveLength(3)
    const external = malaria.findAll('.external-data .input-file')
    expect(external.map(e => e.text().split(':')[0])).toEqual(['Fokontany', 'Health centres'])
    expect(external[0].find('.dropzone').classes()).not.toContain('is-disabled')
    expect(external[1].find('.dropzone').classes()).toContain('is-disabled')
    expect(external[1].text()).toContain('can be changed while a CSB run is open')
    // The repo's defaults: offered under each input, usable only where an upload is.
    const useDefault = (input: typeof external[0]) => input.findAll('.default-status button').find(b => b.text() === 'Use default')
    expect(malaria.find('.input-file .default-status').text()).toContain('config_malaria.json')
    expect(external[0].find('.default-status').exists()).toBe(false) // no default for fkt in this mock
    expect(useDefault(external[1])!.attributes('disabled')).toBeDefined()
    applyDefaultFile.mockResolvedValue('input/config.json')
    await useDefault(malaria.find('.input-file'))!.trigger('click')
    await flushPromises()
    expect(applyDefaultFile).toHaveBeenCalledWith('config', false)
    const [adj, com, csb] = malaria.findAll('.level-column')
    // The items live in each run's "Steps" drawer, rendered only once opened.
    for (const level of [adj, com, csb]) await level.findAll('button').find(b => b.text() === 'Steps')!.trigger('click')
    expect(adj.text()).toContain('Published')
    expect(adj.findAll('.item')).toHaveLength(7)
    expect(csb.findAll('.item')).toHaveLength(8) // calc_orgunit_alerts
    expect(csb.text()).toContain('Alert thresholds (CSB only)')
    expect(com.text()).toContain('Disease data')
    expect(com.text()).toContain('fetch_disease')
    expect(csb.text()).toContain('Available once the open run is done')

    expect(adj.find('progress').attributes()).toMatchObject({ value: '1', max: '7' })
    expect(com.find('[role="dialog"]').text()).toContain('Disease data')
    const launchButtons = com.findAll('button').filter(b => b.text() === 'Launch')
    expect(launchButtons).toHaveLength(1) // only what etlhub marks launchable
    await launchButtons[0].trigger('click')
    await flushPromises()
    expect(launchJob).toHaveBeenCalledWith('fetch_disease', false)
    wrapper.unmount()
  })

  it('reads the report of the run awaiting approval, then approves it', async () => {
    decideRun.mockResolvedValue(undefined)
    getCheckpoints.mockResolvedValue(forecastState('COM/Malaria', { 'COM/Malaria:approve': ['pending', true] }))
    const wrapper = await mountPage()

    expect(wrapper.find('.todo').text()).toContain('approve Malaria · Community sites (COM).')
    const com = wrapper.find('#forecast-Malaria').findAll('.level-column')[1]
    expect(com.text()).toContain('To approve')
    await com.findAll('button').find(b => b.text() === 'Steps')!.trigger('click')
    expect(com.text()).toContain('Waiting for your decision')
    await com.findAll('button').find(b => b.text() === 'Read and approve')!.trigger('click')
    await flushPromises()
    expect(apiGet).toHaveBeenLastCalledWith('/output/forecast_report.html', { responseType: 'text' })

    await wrapper.findAll('button').find(b => b.text() === 'Approve')!.trigger('click')
    await flushPromises()
    expect(decideRun).toHaveBeenCalledWith('approve')
    wrapper.unmount()
  })

  it('opens a run when none is open, and shows the report kept for a published run', async () => {
    openRun.mockResolvedValue({})
    const published = forecastState(null, { 'ADJ/Malaria:post_forecast': ['success'] })
    published.steps[1].items.find(i => i.item === 'ADJ/Malaria:post_forecast')!.updated_at = '2026-10-13T14:02:11'
    getCheckpoints.mockResolvedValue(published)
    const wrapper = await mountPage()

    const [adj, com] = wrapper.find('#forecast-Malaria').findAll('.level-column')
    await adj.findAll('button').find(b => b.text() === 'Steps')!.trigger('click')
    expect(adj.findAll('.item-time').map(t => t.text())).toEqual(['Last update: 2026-10-13 14:02']) // a success only
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
