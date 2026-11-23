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
const pausePass = vi.fn()
const abandonPass = vi.fn()
const apiGet = vi.fn()
const applyDefaultFile = vi.fn()
const getImportAvailability = vi.fn()
const getFetchedImports = vi.fn()
const push = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('@/services/pipeline', () => ({
  getCheckpoints: (...args: unknown[]) => getCheckpoints(...args),
  launchJob: (...args: unknown[]) => launchJob(...args),
  setMode: (...args: unknown[]) => setMode(...args),
  setCycle: (...args: unknown[]) => setCycle(...args),
  decideRun: (...args: unknown[]) => decideRun(...args),
  decideImports: (...args: unknown[]) => decideImports(...args),
  openRun: (...args: unknown[]) => openRun(...args),
  abandonRun: (...args: unknown[]) => abandonRun(...args),
  pausePass: (...args: unknown[]) => pausePass(...args),
  abandonPass: (...args: unknown[]) => abandonPass(...args),
  getImportAvailability: (...args: unknown[]) => getImportAvailability(...args),
  getFetchedImports: (...args: unknown[]) => getFetchedImports(...args)
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
vi.mock('@/views/TrackerView/components/JobLogsPanel.vue', async () => {
  const { defineComponent, h } = await import('vue')
  return { default: defineComponent({ props: ['jobId'], setup: p => () => h('div', { 'data-test': 'job-logs', 'data-job': p.jobId }) }) }
})
vi.mock('vue3-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn(), loading: vi.fn(), dismiss: vi.fn() } }))

import Dashboard from '@/views/Dashboard/Dashboard.vue'

const item = (name: string, status = 'pending', launchable = false) => ({ item: name, status, job_id: null, updated_at: null, launchable })

function state(overrides: object = {}) {
  return {
    cycle: '202610', current_step: 'data_import', run: null, lock: null, test_mode: false, dry_run: true,
    pass: { id: '3f9c1a2b', cycle: '202610', state: 'active', started_at: 't', started_by: 'jdoe' },
    steps: [
      { step: 'data_import', done: false, accessible: true, items: [{ ...item('import_gee', 'success', true), updated_at: '2026-10-13T14:02:11' }, item('approve_imports'), item('build_analytics')] },
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
    run: couple && { pass_id: '3f9c1a2b', couple, state: 'open', disease_code: 'x', ou_level: '6', alert_name: null, opened_at: 't' },
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

  it('the last breadcrumb goes to the current item: scrolls to its card, blinks it orange when no job runs', async () => {
    getCheckpoints.mockResolvedValue(state({ steps: [
      { step: 'data_import', done: false, accessible: true, items: [item('import_gee', 'success', true),
        item('approve_imports', 'success', true), item('build_analytics', 'pending', true)] },
      { step: 'forecast', done: false, accessible: false, items: [] },
      { step: 'system_update', done: false, accessible: false, items: [item('build_analytics'), item('update_key')] }
    ] }))
    const wrapper = await mountPage()
    expect(wrapper.find('[data-test="position"] [aria-current="page"]').text()).toBe('Build Analytics')

    await wrapper.find('[data-test="position-link"]').trigger('click')
    await flushPromises()
    // Step ①'s Build Analytics is done from the approval's dialog: its card is the one pointed to
    const card = wrapper.find('[data-section="dataImport"] [data-item="approve_imports"]')
    expect(card.attributes('data-attention')).toBeDefined()
    expect(wrapper.find('[data-section="systemUpdate"] [data-attention]').exists()).toBe(false) // not its namesake of step ③
    wrapper.unmount()

    getCheckpoints.mockResolvedValue(state({ lock: { job_id: 'import_gee_1', task: 'import_gee', acquired_at: 't' } }))
    const busy = await mountPage()
    await busy.find('[data-test="position-link"]').trigger('click')
    await flushPromises()
    expect(busy.find('[data-attention]').exists()).toBe(false) // a job runs: nothing to click now
    busy.unmount()
  })

  it('the last breadcrumb of a run opens its Steps dialog at the right stage and blinks the button to click', async () => {
    getCheckpoints.mockResolvedValue(forecastState('COM/Malaria', {
      'config/Malaria': ['success'], 'external_data/fkt': ['success'],
      'COM/Malaria:fetch_disease': ['success', true], 'COM/Malaria:fetch_climate': ['pending', true]
    }))
    const wrapper = await mountPage()
    expect(wrapper.find('[data-test="position"]').text()).toContain('Climate data')

    await wrapper.find('[data-test="position-link"]').trigger('click')
    await flushPromises()
    const com = wrapper.find('#forecast-Malaria').findAll('[data-test="level-column"]')[1]
    const row = com.find('[data-test="steps-dialog"] [data-item="COM/Malaria:fetch_climate"]')
    expect(row.find('button').text()).toBe('Launch')
    expect(row.find('button').attributes('data-attention')).toBeDefined()
    wrapper.unmount()
  })

  it('shows the test mode before step 1 and, with no active pass, switches it on the server', async () => {
    getCheckpoints.mockResolvedValue(state({ pass: null }))
    setMode.mockImplementation(async () => {
      getCheckpoints.mockResolvedValue(state({ pass: null, test_mode: true }))
      return true
    })
    const wrapper = await mountPage()
    expect(wrapper.find('[data-test="mode-frozen"]').exists()).toBe(false)

    const html = wrapper.html()
    // The step's accordion title: the breadcrumb above the toggle also says 'Data Import'
    expect(html.indexOf('mode-toggle')).toBeLessThan(html.lastIndexOf('Data Import'))
    expect(wrapper.text()).toContain('DHIS2: dry run (test mode), the jobs write nothing.') // etlhub's dry_run, from GET /pipeline/checkpoints

    await wrapper.findAll('[data-test="mode-btn"]').find(b => b.text() === 'NO')!.trigger('click') // already active
    await flushPromises()
    expect(setMode).not.toHaveBeenCalled()
    await wrapper.findAll('[data-test="mode-btn"]').find(b => b.text() === 'YES')!.trigger('click')
    await flushPromises()
    expect(setMode).toHaveBeenCalledWith(true, undefined)
    // A mode never shows what happened in the other: Recent Activity starts empty, even without the switch itself
    expect(wrapper.find('[data-test="activity-aside"]').text()).not.toContain('Switch to test mode')
    wrapper.unmount()
  })

  it('freezes the mode while the pass is active', async () => {
    const wrapper = await mountPage() // state(): an active pass

    const buttons = wrapper.findAll('[data-test="mode-btn"]')
    expect(buttons.every(b => b.attributes('disabled') !== undefined)).toBe(true)
    await buttons.find(b => b.text() === 'YES')!.trigger('click')
    await flushPromises()
    expect(setMode).not.toHaveBeenCalled()
    expect(wrapper.find('[data-test="mode-frozen"]').text()).toContain('pause or abandon the cycle')
    wrapper.unmount()
  })

  it('a pass started meanwhile (the page did not know): etlhub asks to pause or abandon it, then gets the choice', async () => {
    getCheckpoints.mockResolvedValue(state({ pass: null }))
    const message = 'Pass 3f9c1a2b (202610) is active in production mode, and a pass lives in one mode'
    setMode
      .mockRejectedValueOnce({ response: { status: 409, data: { code: 'confirmation_required', message, impact: {
        pass_id: '3f9c1a2b', cycle: '202610', mode: 'production', to: 'test', actions: ['pause', 'abandon'] } } } })
      .mockResolvedValueOnce(true)
    const wrapper = await mountPage()

    await wrapper.findAll('[data-test="mode-btn"]').find(b => b.text() === 'YES')!.trigger('click')
    await flushPromises()
    const dialog = wrapper.find('[data-test="impact-dialog"]')
    expect(dialog.text()).toContain(message)
    expect(dialog.text()).not.toContain('Confirm') // two choices instead
    await dialog.find('[role="checkbox"]').trigger('click') // the impact is read
    await dialog.find('[data-test="impact-action-abandon"]').trigger('click')
    await flushPromises()
    expect(setMode).toHaveBeenLastCalledWith(true, 'abandon')
    wrapper.unmount()
  })

  it('shows the cycle as text: the month is chosen on Home', async () => {
    getCheckpoints.mockResolvedValue(state({ pass: null }))
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('Cycle 202610')
    expect(wrapper.text()).toContain('not started: the first launch starts it')
    expect(wrapper.find('input[type="month"]').exists()).toBe(false)
    expect(setCycle).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('while a pass is active, pauses or abandons it from the left panel, under Recent Activity', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout'] }) // the 2 s screen before Home; flushPromises keeps its real setImmediate
    pausePass.mockResolvedValue({})
    abandonPass.mockResolvedValue({})
    const wrapper = await mountPage()

    expect(wrapper.text()).toContain('started by jdoe')
    // Where the pass stands, as a shadcn Breadcrumb next to the cycle: step / next item, the last one is the current page
    const crumbs = wrapper.find('[data-test="position"]')
    expect(crumbs.findAll('li[data-slot="breadcrumb-item"]').map(li => li.text())).toEqual(['Data Import', 'Imports approval'])
    expect(crumbs.find('[aria-current="page"]').text()).toBe('Imports approval')
    const aside = wrapper.find('[data-test="activity-aside"]')
    expect(aside.text().indexOf('Pause the cycle')).toBeGreaterThan(aside.text().indexOf('Recent Activity'))
    expect(aside.text()).toContain('Abandon the cycle')

    await wrapper.findAll('button').find(b => b.text() === 'Pause the cycle')!.trigger('click')
    await flushPromises()
    expect(pausePass).not.toHaveBeenCalled() // a confirmation first
    await wrapper.findAll('button').find(b => b.text() === 'Pause')!.trigger('click')
    await flushPromises()
    expect(pausePass).toHaveBeenCalledTimes(1)
    expect(wrapper.find('[data-test="leaving-screen"]').text()).toContain('Cycle paused. Back to Home')
    expect(push).not.toHaveBeenCalled() // not before the 2 s
    await vi.advanceTimersByTimeAsync(2000)
    expect(push).toHaveBeenLastCalledWith({ name: 'Home' })

    push.mockClear()
    await wrapper.findAll('button').find(b => b.text() === 'Abandon the cycle')!.trigger('click')
    await flushPromises()
    expect(abandonPass).not.toHaveBeenCalled() // a confirmation first
    await wrapper.findAll('button').find(b => b.text() === 'Abandon')!.trigger('click')
    await flushPromises()
    expect(abandonPass).toHaveBeenCalledWith('3f9c1a2b')
    expect(wrapper.find('[data-test="leaving-screen"]').text()).toContain('Cycle abandoned.')
    await vi.advanceTimersByTimeAsync(2000)
    expect(push).toHaveBeenLastCalledWith({ name: 'Home' })
    wrapper.unmount()
    vi.useRealTimers()
  })

  it('stays on the page when the pause fails', async () => {
    pausePass.mockRejectedValue(new Error('boom'))
    const wrapper = await mountPage()
    await wrapper.findAll('button').find(b => b.text() === 'Pause the cycle')!.trigger('click')
    await wrapper.findAll('button').find(b => b.text() === 'Pause')!.trigger('click')
    await flushPromises()
    expect(push).not.toHaveBeenCalled()
    expect(wrapper.find('[data-test="leaving-screen"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('shows the GEE variables the pass chose for Import GEE', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-test="pass-gee"]').text()).toBe('Import GEE: all available variables') // started by a launch
    wrapper.unmount()

    getCheckpoints.mockResolvedValue(state({ pass: { id: '3f9c1a2b', cycle: '202610', state: 'active', started_at: 't',
      started_by: 'jdoe', gee_variables: 'v1,v3' } }))
    const chosen = await mountPage()
    expect(chosen.find('[data-test="pass-gee"]').text()).toBe('Import GEE: v1, v3')
    chosen.unmount()
  })

  it('sends a paused cycle to the Journal, without the pass buttons', async () => {
    getCheckpoints.mockResolvedValue(state({ pass: { id: '3f9c1a2b', cycle: '202610', state: 'paused', started_at: 't', started_by: 'jdoe' } }))
    const wrapper = await mountPage()

    expect(wrapper.text()).toContain('paused: resume it from Home or the Journal')
    expect(wrapper.text()).not.toContain('Pause the cycle')
    wrapper.unmount()
  })

  it('enables only the cards etlhub says are launchable', async () => {
    launchJob.mockResolvedValue('job')
    const wrapper = await mountPage()

    const cards = wrapper.findAll('[data-test="action-card"]')
    const gee = cards.find(c => c.text().includes('Import GEE'))!
    const build = cards.find(c => c.text().includes('Update Key'))! // not launchable
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

  it('shows etlhub\'s DRYRUN (DRYRUN = TEST MODE), read only', async () => {
    getCheckpoints.mockResolvedValue(state({ dry_run: false, pass: { id: '3f9c1a2b', cycle: '202610', state: 'active',
      started_at: 't', started_by: 'jdoe', dry_run: true } })) // production; a stored value never counts
    const wrapper = await mountPage()

    expect(wrapper.find('[data-test="dry-run-hint"]').text()).toContain('no dry run (production), the jobs write to DHIS2')
    expect(wrapper.find('[data-test="dry-run-btn"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('asks for the approval checkbox before resending with confirm=true', async () => {
    launchJob
      .mockRejectedValueOnce({ response: { status: 409, data: { code: 'confirmation_required', message: 'import_gee is already in success',
        impact: { item: 'import_gee', step: 'data_import', reset_items: [], blocked_steps: ['forecast', 'system_update'] } } } })
      .mockResolvedValueOnce('job_2')
    const wrapper = await mountPage()

    await wrapper.findAll('[data-test="action-card"]').find(c => c.text().includes('Import GEE'))!.trigger('click')
    await flushPromises()
    const dialog = wrapper.find('[data-test="impact-dialog"]')
    expect(dialog.text()).toContain('forecast, system_update')
    const confirmButton = dialog.findAll('button').find(b => b.text() === 'Confirm')!
    expect(confirmButton.attributes('disabled')).toBeDefined()

    await dialog.find('[role="checkbox"]').trigger('click')
    await confirmButton.trigger('click')
    await flushPromises()
    expect(launchJob).toHaveBeenLastCalledWith('import_gee', true)
    wrapper.unmount()
  })

  it('opens the import availability report from the Details button of Data Import, with a loader first', async () => {
    let answer!: (v: unknown) => void
    getImportAvailability.mockReturnValue(new Promise(resolve => (answer = resolve)))
    const wrapper = await mountPage()

    expect(wrapper.find('[data-test="accordion-header"]').findAll('button')).toHaveLength(1) // the toggle only, nothing next to the title
    const details = wrapper.find('[data-test="imports-approval"]').findAll('button').find(b => b.text() === 'Details')!
    await details.trigger('click')
    expect(wrapper.find('[data-test="availability-dialog"]').text()).toContain('Checking DHIS2')

    const el = { last_updated: null, error: null }
    answer({
      dhis_url: 'http://dhis2.test', last_analytics: null,
      imports: [{ task: 'import_pivot_com', periods: ['202608', '202609'], org_units: 'ou:LEVEL-6;P1',
        checked_at: '2026-10-26T08:00:00', checked_by: 'jdoe', pass_id: '3f9c1a2b', reused: true, elements: [
        { ...el, code: 'pridec_historic_COMMalaria', raw: { 202608: 67, 202609: 0 }, analytics: { 202608: 60, 202609: 0 }, imported: false, analytics_up_to_date: false },
        { ...el, code: 'pridec_historic_COMDiarrhea', raw: { 202608: 5, 202609: 6 }, analytics: { 202608: 5, 202609: 6 }, imported: true, analytics_up_to_date: true }
      ] }]
    })
    await flushPromises()

    const dialog = wrapper.find('[data-test="availability-dialog"]')
    expect(dialog.text()).toContain('Import Pivot COM')
    const malaria = dialog.find('tr[data-code="pridec_historic_COMMalaria"]')
    expect(malaria.findAll('td').map(td => td.text())).toEqual(['67 60', 'N/A', '✗'])
    expect(malaria.find('[aria-label="Not imported"]').exists()).toBe(true)
    expect(dialog.find('tr[data-code="pridec_historic_COMDiarrhea"] .is-ok').text()).toBe('✓')
    expect(dialog.text()).toContain('pridec_historic_COMMalaria: analytics behind the stored values, run Build Analytics.')
    expect(dialog.find('[data-test="availability-origin"]').text()).toMatch(/^reused checked .* by jdoe · pass 3f9c1a2b$/) // shared by another user

    await dialog.findAll('button').find(b => b.text() === 'Refresh')!.trigger('click')
    expect(getImportAvailability).toHaveBeenLastCalledWith(true)
    wrapper.unmount()
  })

  it('shows the error of an availability check that could not run', async () => {
    getImportAvailability.mockRejectedValue(new Error('500'))
    const wrapper = await mountPage()

    await wrapper.find('[data-test="imports-approval"]').findAll('button').find(b => b.text() === 'Details')!.trigger('click')
    await flushPromises()

    expect(wrapper.find('.availability-dialog [role="alert"]').text()).toBe('Could not check the imported data')
    wrapper.unmount()
  })

  it('reviews and approves the fetched Pivot data line by line, shows the post, then offers Build Analytics', async () => {
    getCheckpoints.mockResolvedValue(state({ steps: [
      { step: 'data_import', done: false, accessible: true, items: [item('import_gee', 'success', true), item('approve_imports', 'pending', true), item('build_analytics')] },
      { step: 'forecast', done: false, accessible: false, items: [] },
      { step: 'system_update', done: false, accessible: false, items: [] }
    ] }))
    decideImports.mockResolvedValue(undefined)
    const text = (max: number) => `numNA: 0 | minimum value: 0 | maximum value: ${max} | negative values: 0 | number of values: 279`
    const el = (data_element: string, flagged: boolean) => ({
      data_element, rows: 279, flagged, text: text(flagged ? 164 : 35),
      error: flagged ? `Potential errors in data to be imported: 1 orgUnits exceed case threshold of 100. ${text(164)}` : null
    })
    getFetchedImports.mockResolvedValue([
      { task: 'import_pivot_com', elements: [el('pridec_historic_COMMalaria', false), el('pridec_historic_COMRespinf', true)] },
      { task: 'import_pivot_csb', elements: [] }
    ])
    const wrapper = await mountPage()

    const grid = wrapper.find('[data-section="dataImport"]')
    expect(grid.find('[data-item="build_analytics"]').exists()).toBe(false) // launched from the approval's dialog
    expect(wrapper.find('[data-test="imports-approval"]').findAll('button').map(b => b.text())).toEqual(['Details']) // read only
    const card = grid.find('[data-item="approve_imports"]')
    expect(card.text()).toContain('Review and Approve')
    await card.trigger('click')
    await flushPromises()

    const dialog = wrapper.find('[data-test="approval-dialog"]')
    const row = (name: string) => dialog.find(`tr[data-element="${name}"]`)
    expect(row('pridec_historic_COMRespinf').text()).toContain('Flagged')
    expect(row('pridec_historic_COMRespinf').find('[data-test="stat-max"]').text()).toBe('164') // the check, one column each
    expect(row('pridec_historic_COMRespinf').text()).not.toContain('numNA')
    expect(dialog.findAll('[data-test="approval-problems"]').map(r => r.text())).toEqual(
      ['↳ 1 orgUnits exceed case threshold of 100']) // the flagged line's problem only, the summary not repeated
    expect(dialog.find('[data-test="approval-empty"]').text()).toContain('Nothing fetched') // CSB
    const footer = dialog.find('[data-test="preview-footer"]')
    expect(footer.findAll('button').map(b => [b.text(), b.attributes('disabled') !== undefined])).toEqual([
      ['Reject', true], ['Approve and post 1', false]]) // flagged unchecked; nothing approved yet: nothing to reject

    await row('pridec_historic_COMRespinf').trigger('click') // a whole line selects
    await row('pridec_historic_COMMalaria').trigger('click') // and unselects
    let posted!: () => void
    decideImports.mockReturnValue(new Promise<void>(resolve => { posted = resolve })) // etlhub posts synchronously
    await dialog.find('[data-test="approve-imports"]').trigger('click')
    await flushPromises()
    expect(decideImports).toHaveBeenCalledWith('approve', ['pridec_historic_COMRespinf'], false)
    const post = () => wrapper.find('[data-test="approval-post"]') // the dialog stays open on the post
    expect(post().find('[data-test="posting-bar"]').exists()).toBe(true)
    expect(post().text()).toContain('pridec_historic_COMRespinf')
    expect(wrapper.find('[data-test="build-analytics"]').exists()).toBe(false)

    getCheckpoints.mockResolvedValue(state({ steps: [
      { step: 'data_import', done: false, accessible: true, items: [item('import_gee', 'success', true),
        { ...item('approve_imports', 'success', true), job_id: 'approve_imports_1a2b3c4d' }, item('build_analytics', 'pending', true)] },
      { step: 'forecast', done: false, accessible: false, items: [] },
      { step: 'system_update', done: false, accessible: false, items: [] }
    ] }))
    posted()
    await flushPromises()
    expect(post().find('[data-test="posting-bar"]').exists()).toBe(false)
    expect(post().find('[data-test="job-logs"]').attributes('data-job')).toBe('approve_imports_1a2b3c4d') // the post's steps
    expect(grid.find('[data-item="approve_imports"]').text()).toContain('Approved: Build Analytics to launch')

    launchJob.mockResolvedValue({ jobId: 'build_analytics_1', requestId: 'r' })
    await wrapper.find('[data-test="build-analytics"]').trigger('click')
    await flushPromises()
    expect(launchJob).toHaveBeenCalledWith('build_analytics', false)
    expect(wrapper.find('[data-test="approval-dialog"]').exists()).toBe(false) // the toast follows the build
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

    const runs = wrapper.find('[data-test="forecast-runs"]')
    expect(runs.find('[data-test="todo"]').text()).toContain('launch “Disease data” for Malaria · Community sites (COM).')
    expect(runs.findAll('[data-test="disease-card"]')).toHaveLength(3)
    // One tab per disease, the open run's (Malaria) first; the other tabs stay mounted, hidden.
    const tabs = () => runs.findAll('[data-test="disease-tabs"] [role="tab"]')
    expect(tabs().map(t => t.text())).toEqual(['Malaria', 'Diarrhea', 'Respiratory infections'])
    expect(tabs().map(t => t.attributes('aria-selected'))).toEqual(['true', 'false', 'false'])
    await tabs()[2].trigger('mousedown', { button: 0 })
    expect(tabs().map(t => t.attributes('aria-selected'))).toEqual(['false', 'false', 'true'])
    expect(runs.find('#forecast-Malaria').element.closest('[role="tabpanel"]')!.getAttribute('data-state')).toBe('inactive') // hidden by CSS
    expect(runs.findAll('[data-test="level-carousel"] [role="group"]')).toHaveLength(9) // 3 runs per disease
    await tabs()[0].trigger('mousedown', { button: 0 })
    const malaria = runs.find('#forecast-Malaria')
    expect(malaria.text()).toContain('1 of 3 levels published')
    // Only the open run has steps to show: its whole card opens them, highlighted.
    expect(malaria.findAll('[data-test="dropzone"]')).toHaveLength(0) // the input files are in the steps dialog, closed
    const [adj, com, csb] = malaria.findAll('[data-test="level-column"]')
    expect(malaria.findAll('button').some(b => b.text() === 'Steps')).toBe(false)
    expect([adj, com, csb].map(l => l.attributes('aria-current') === 'true')).toEqual([false, true, false])
    expect([adj, com, csb].map(l => l.find('[data-test="card-steps"]').exists())).toEqual([false, true, false])
    expect([adj, csb].map(l => l.find('[data-test="steps-dialog"]').exists())).toEqual([false, false])
    await com.find('[data-test="card-steps"]').trigger('click')
    await flushPromises()
    const steps = com.find('[data-test="steps-dialog"]')
    expect(steps.findAll('[data-test="dropzone"]')).toHaveLength(2)
    expect(steps.findAll('button').filter(b => b.text() === 'Close')).toHaveLength(1) // shadcn's cross, the only close
    // The run's input files first, then its jobs.
    const inputs = com.findAll('[data-test="item"]').filter(i => i.find('[data-test="dropzone"]').exists())
    expect(inputs.map(i => i.find('[data-test="item-tech"]').text())).toEqual(['config/Malaria', 'external_data/fkt'])
    expect(inputs[0].text()).toContain('config_malaria.json')
    expect(inputs[0].text()).toContain('✓ provided · same file for the 3 Malaria runs')
    expect(inputs.map(i => i.find('[data-test="dropzone"]').attributes('aria-disabled') === 'true')).toEqual([false, false])
    // The repo's defaults: offered under each input.
    const useDefault = (input: typeof inputs[0]) => input.findAll('[data-test="default-status"] button').find(b => b.text() === 'Use default')
    expect(inputs[0].find('[data-test="default-status"]').text()).toContain('config_malaria.json')
    expect(inputs[1].find('[data-test="default-status"]').exists()).toBe(false) // no default for fkt in this mock
    applyDefaultFile.mockResolvedValue('input/config.json')
    await useDefault(inputs[0])!.trigger('click')
    await flushPromises()
    expect(applyDefaultFile).toHaveBeenCalledWith('config', false)
    expect(adj.text()).toContain('Published')
    expect(com.findAll('[data-test="item"]')).toHaveLength(8) // 2 input files + 6 jobs: the data check is a button
    // All shown at once, in 4 columns; the data check button waits for the 5 items before it.
    const columns = com.findAll('[data-test="steps-column"]')
    expect(columns.map(c => c.findAll('[data-test="item-tech"]').map(t => t.text()))).toEqual([
      ['config/Malaria', 'external_data/fkt'], ['fetch_disease', 'fetch_climate', 'fetch_geojson'],
      ['forecast', 'approve'], ['post_forecast']])
    expect(columns[1].find('[data-test="data-check"]').text()).toContain('Available once the input files and the 3 fetches are done')
    expect(columns[1].findAll('[data-test="data-check"] button').map(b => [b.text(), b.attributes('disabled') !== undefined]))
      .toEqual([['Run the data check', true]])
    // The stepper: a column's step is done once all its items succeed (here, the 2 input files).
    expect(columns.map(c => c.find('[data-test="step"]').text())).toEqual(
      ['✓Input files (done)', '2Prepare the data', '3Forecast and approval', '4Publication'])
    expect(com.text()).toContain('Disease data')
    expect(com.text()).toContain('fetch_disease')
    expect(com.findAll('[data-test="item-time"]').map(t => t.text())).toEqual(['Last update: 2026-10-13 14:02']) // a success only
    expect(csb.text()).toContain('Available once the open run is done')

    expect(adj.find('[role="progressbar"]').attributes()).toMatchObject({ 'aria-valuenow': '3', 'aria-valuemax': '9' }) // both shared files are provided
    expect(com.find('[data-test="steps-dialog"]').text()).toContain('Disease data')
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

    expect(wrapper.find('[data-test="todo"]').text()).toContain('approve Malaria · Community sites (COM).')
    const com = wrapper.find('#forecast-Malaria').findAll('[data-test="level-column"]')[1]
    expect(com.text()).toContain('To approve')
    await com.find('[data-test="card-steps"]').trigger('click')
    // The data check succeeded: it can be relaunched, next to the approval waiting.
    expect(com.find('[data-test="data-check"] button').text()).toBe('Relaunch the data check')
    expect(com.text()).toContain('Waiting for your decision')
    // Read and approve: on the card, and on the approval item of the dialog.
    const approveItem = com.find('[data-test="steps-dialog"] [data-job="approve"]')
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

    const [adj, com] = wrapper.find('#forecast-Malaria').findAll('[data-test="level-column"]')
    expect(adj.find('[data-test="card-steps"]').exists()).toBe(false) // no open run: no steps to show
    await com.findAll('button').find(b => b.text() === 'Open')!.trigger('click')
    await flushPromises()
    expect(openRun).toHaveBeenCalledWith('COM', 'Malaria', false)

    await adj.findAll('button').find(b => b.text() === 'View report')!.trigger('click')
    await flushPromises()
    expect(apiGet).toHaveBeenLastCalledWith('/pipeline/runs/ADJ/Malaria/report', { responseType: 'text' })
    wrapper.unmount()
  })

  it("shows the open run's disease tab, and goes back to it on the breadcrumb's link", async () => {
    getCheckpoints.mockResolvedValue(forecastState('CSB/Respinf', { 'config/Respinf': ['pending', true] }))
    const wrapper = await mountPage()
    const selected = () => wrapper.findAll('[data-test="disease-tabs"] [role="tab"]').map(t => t.attributes('aria-selected'))
    expect(selected()).toEqual(['false', 'false', 'true'])

    await wrapper.findAll('[data-test="disease-tabs"] [role="tab"]')[0].trigger('mousedown', { button: 0 })
    expect(selected()).toEqual(['true', 'false', 'false'])
    await wrapper.find('[data-test="position-link"]').trigger('click')
    await flushPromises()
    expect(selected()).toEqual(['false', 'false', 'true'])
    wrapper.unmount()
  })

  it('abandons the open run from the header of its steps dialog, after a confirmation, admin or not', async () => {
    abandonRun.mockResolvedValue('COM/Malaria')
    getCheckpoints.mockResolvedValue(forecastState('COM/Malaria'))
    const wrapper = await mountPage()
    const com = wrapper.find('#forecast-Malaria').findAll('[data-test="level-column"]')[1]
    await com.find('[data-test="card-steps"]').trigger('click')
    await flushPromises()

    await com.find('[data-test="steps-dialog"] header [data-test="abandon-run"]').trigger('click')
    await flushPromises()
    expect(abandonRun).not.toHaveBeenCalled() // a confirmation first
    expect(wrapper.text()).toContain('Abandon the run COM/Malaria?')
    await wrapper.findAll('button').find(b => b.text() === 'Abandon the run')!.trigger('click')
    await flushPromises()
    expect(abandonRun).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })
})
