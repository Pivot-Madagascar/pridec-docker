import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'

const getCheckpoints = vi.fn()
const getCycles = vi.fn()
const setCycle = vi.fn()
const resumePass = vi.fn()
const startPass = vi.fn()
const setMode = vi.fn()
vi.mock('@/services/pipeline', () => ({
  getCheckpoints: (...args: unknown[]) => getCheckpoints(...args),
  getCycles: (...args: unknown[]) => getCycles(...args),
  setCycle: (...args: unknown[]) => setCycle(...args),
  resumePass: (...args: unknown[]) => resumePass(...args),
  startPass: (...args: unknown[]) => startPass(...args),
  setMode: (...args: unknown[]) => setMode(...args),
  journalCsvUrl: vi.fn()
}))
vi.mock('@/services/inputs', () => ({ getInputFiles: vi.fn().mockResolvedValue({}), getDefaultFiles: vi.fn().mockResolvedValue({}) }))
vi.mock('@/services/config', () => ({
  configService: {
    get: vi.fn().mockResolvedValue({
      dhis_url: 'https://dhis2.example', has_dhis_token: true, dhis_token_expires_at: null, parent_ou: 'OU_PARENT',
      ou_level: 5, disease_code: 'MAL', log_level: 'INFO', gee_variables: ['v1', 'v2', 'v3']
    })
  }
}))
const push = vi.fn()
const replace = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push, replace }) }))
vi.mock('vue3-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn(), loading: vi.fn(), dismiss: vi.fn() } }))

import HomeView from '@/views/Home/HomeView.vue'

const pass = (id: string, cycle: string, state: string, mode = 'production') => ({
  id, cycle, state, started_at: '2026-10-16T09:00:00.000000', started_by: 'jdoe', mode, events: 3, last_at: null
})
const checkpoints = (over: object = {}) => ({
  cycle: '202610', pass: null, current_step: null, run: null, lock: null, test_mode: false, dry_run: false, steps: [], ...over
})

let mounted: VueWrapper | null = null
async function mountPage() {
  const wrapper = (mounted = mount(HomeView, { attachTo: document.body })) // attached: the button submits the form
  await flushPromises()
  return wrapper
}
type Page = Awaited<ReturnType<typeof mountPage>>
const button = (wrapper: Page, text: string) => wrapper.findAll('button').find(b => b.text() === text)!
const startButton = (wrapper: Page) => button(wrapper, 'Start')
// The opening dialog asks the cycle; Continue moves it to the top of the page.
async function closeCycleDialog(wrapper: Page) {
  await button(wrapper, 'Continue').trigger('click')
  await flushPromises()
}
// Picks a month of the year shown ('YYYY-MM'), in the cycle picker shown (the dialog's, then the top of the page's).
async function pickMonth(wrapper: Page, month: string) {
  await wrapper.find('[data-test="cycle-picker"]').trigger('click')
  await flushPromises()
  await wrapper.find(`[data-reka-month-picker-cell-trigger][data-value^="${month}"]`).trigger('click')
  await flushPromises()
}

describe('HomeView', () => {
  afterEach(() => {
    mounted?.unmount()
    vi.useRealTimers()
  })

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers({ toFake: ['Date'] }) // only the clock: the current month is the default cycle
    vi.setSystemTime(new Date(2026, 9, 20))
    getCheckpoints.mockResolvedValue(checkpoints())
    getCycles.mockResolvedValue([
      { cycle: '202610', target: true, passes: [pass('pppp1111', '202610', 'paused'), pass('tttt2222', '202610', 'paused', 'test')] },
      { cycle: '202609', target: false, passes: [pass('cccc3333', '202609', 'complete')] }
    ])
  })

  it('offers the paused pass of the chosen month and mode, resumes it and goes to the forecast page', async () => {
    resumePass.mockResolvedValue({})
    const wrapper = await mountPage()

    // The cycle is asked first, the current month by default, then shown at the top of the page
    expect(wrapper.find('[data-test="cycle-dialog"]').exists()).toBe(true)
    expect(wrapper.findAll('[data-test="cycle-picker"]')).toHaveLength(1)
    expect(wrapper.find('[data-test="cycle-picker"]').attributes('value')).toBe('2026-10')
    // Months only, never days; no future month
    await wrapper.find('[data-test="cycle-dialog"] [data-test="cycle-picker"]').trigger('click')
    await flushPromises()
    expect(wrapper.findAll('[data-reka-month-picker-cell-trigger]')).toHaveLength(12)
    expect(wrapper.find('[data-reka-calendar-cell-trigger]').exists()).toBe(false)
    expect(wrapper.find('[data-reka-month-picker-cell-trigger][data-value^="2026-11"]').attributes('data-disabled')).toBeDefined()
    await wrapper.find('[data-test="cycle-picker"]').trigger('click') // closes the popover
    await flushPromises()
    await closeCycleDialog(wrapper)
    expect(wrapper.find('[data-test="cycle-dialog"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="cycle-picker"]').attributes('value')).toBe('2026-10')
    expect(wrapper.text()).toContain('pppp1111')
    expect(wrapper.text()).not.toContain('tttt2222') // a test pass is not resumed in production
    expect(wrapper.find('[role="radio"][value="new"]').attributes('disabled')).toBeUndefined() // a new pass, after a confirm
    // The parameters of the pass
    expect(wrapper.text()).toContain('OU_PARENT')
    expect(wrapper.text()).toContain('https://dhis2.example')
    expect(wrapper.text()).toContain('No dry run: jobs write to DHIS2') // production: DRYRUN = TEST MODE = false

    await startButton(wrapper).trigger('click')
    await flushPromises()
    expect(resumePass).toHaveBeenCalledWith('pppp1111')
    expect(setCycle).not.toHaveBeenCalled()
    expect(push).toHaveBeenCalledWith({ name: 'Dashboard' })
  })

  it('starts a new pass on another month: sends the month, starts the pass, then goes to the forecast page', async () => {
    setCycle.mockResolvedValue(undefined)
    startPass.mockResolvedValue(undefined)
    const wrapper = await mountPage()

    await closeCycleDialog(wrapper)
    await pickMonth(wrapper, '2026-09')
    expect(wrapper.find('[data-test="cycle-picker"]').attributes('value')).toBe('2026-09')
    expect(wrapper.find('[data-reka-month-picker-cell-trigger]').exists()).toBe(false) // closed after the pick
    expect(wrapper.text()).toContain('complete') // the redo asks a confirm
    await startButton(wrapper).trigger('click')
    await flushPromises()
    expect(setCycle).toHaveBeenCalledWith('202609')
    expect(startPass).toHaveBeenCalledWith(false, ['v1', 'v2', 'v3'])
    expect(resumePass).not.toHaveBeenCalled()
    expect(push).toHaveBeenCalledWith({ name: 'Dashboard' })
  })

  it('a new pass imports the GEE variables left checked; a paused one keeps its own', async () => {
    getCycles.mockResolvedValue([{ cycle: '202610', target: true, passes: [
      { ...pass('pppp1111', '202610', 'paused'), gee_variables: 'v1,v3' }, pass('oooo0000', '202610', 'paused')] }])
    startPass.mockResolvedValue(undefined)
    const wrapper = await mountPage()
    await closeCycleDialog(wrapper)

    // The paused pass is chosen first: its own variables, no checkbox
    expect(wrapper.find('[data-test="gee-choice"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('GEE_VARIABLESv1, v3')
    await wrapper.find('[role="radio"][value="oooo0000"]').trigger('click') // started by a launch: all of them
    expect(wrapper.text()).toContain('GEE_VARIABLESall available variables')

    await wrapper.find('[role="radio"][value="new"]').trigger('click')
    await flushPromises()
    const boxes = wrapper.findAll('[data-test="gee-choice"] [role="checkbox"]')
    expect(boxes.map(b => b.attributes('aria-checked'))).toEqual(['true', 'true', 'true']) // all by default
    await boxes[1].trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('GEE_VARIABLESv1, v3')
    await boxes[0].trigger('click')
    await boxes[2].trigger('click')
    await flushPromises()
    expect(startButton(wrapper).attributes('disabled')).toBeDefined() // none left
    await boxes[2].trigger('click')
    await flushPromises()

    await startButton(wrapper).trigger('click')
    await flushPromises()
    expect(startPass).toHaveBeenCalledWith(false, ['v3'])
  })

  it('DRYRUN follows the mode, never chosen; a paused pass shows the configuration it started with', async () => {
    getCheckpoints.mockResolvedValue(checkpoints({ test_mode: true, dry_run: true })) // DRYRUN = TEST MODE, from etlhub
    getCycles.mockResolvedValue([{ cycle: '202610', target: true, passes: [{ ...pass('pppp1111', '202610', 'paused', 'test'),
      gee_variables: null, parent_ou: 'OU_FIXED', log_level: 'DEBUG', dry_run: false, dhis_url: 'https://old.dhis2' }] }])
    startPass.mockResolvedValue(undefined)
    const wrapper = await mountPage()
    await closeCycleDialog(wrapper)

    // Resume: its own values, not today's Admin Config or login; DRYRUN: the mode's, whatever the pass stored
    for (const value of ['OU_FIXED', 'DEBUG', 'https://old.dhis2', 'Dry run: nothing is written']) expect(wrapper.text()).toContain(value)
    expect(wrapper.find('[data-test="dry-run-btn"]').exists()).toBe(false)

    await wrapper.find('[role="radio"][value="new"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('OU_PARENT') // a new pass fixes today's values
    expect(wrapper.find('[data-test="dry-run-btn"]').exists()).toBe(false) // no Dry run choice for a new pass either
    await startButton(wrapper).trigger('click')
    await flushPromises()
    expect(startPass).toHaveBeenCalledWith(false, ['v1', 'v2', 'v3']) // no dry_run sent
  })

  it('starts a new pass beside a paused one after the confirm, then goes to the forecast page', async () => {
    startPass
      .mockRejectedValueOnce({ response: { status: 409, data: {
        code: 'confirmation_required', message: 'Pass pppp1111 of cycle 202610 is paused: resend with confirm=true',
        impact: { cycle: '202610', paused_pass: 'pppp1111' } } } })
      .mockResolvedValueOnce(undefined)
    const wrapper = await mountPage()

    await closeCycleDialog(wrapper)
    await wrapper.find('[role="radio"][value="new"]').trigger('click')
    await startButton(wrapper).trigger('click')
    await flushPromises()
    expect(push).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Pass pppp1111 of cycle 202610 is paused')

    await wrapper.find('[data-test="impact-dialog"] [role="checkbox"]').trigger('click') // the impact is read
    await wrapper.findAll('button').find(b => b.text() === 'Confirm')!.trigger('click')
    await flushPromises()
    expect(startPass).toHaveBeenLastCalledWith(true, ['v1', 'v2', 'v3'])
    expect(resumePass).not.toHaveBeenCalled()
    expect(push).toHaveBeenCalledWith({ name: 'Dashboard' })
  })

  it('stays on the page when the server refuses', async () => {
    setCycle.mockRejectedValue({ response: { status: 409, data: { detail: 'A job is running' } } })
    const wrapper = await mountPage()

    await closeCycleDialog(wrapper)
    await pickMonth(wrapper, '2026-09')
    await startButton(wrapper).trigger('click')
    await flushPromises()
    expect(setCycle).toHaveBeenCalled()
    expect(push).not.toHaveBeenCalled()
  })

  it('sends the user to the forecast page while a pass is active, without sending anything', async () => {
    getCheckpoints.mockResolvedValue(checkpoints({ pass: pass('aaaa4444', '202610', 'active') }))
    const wrapper = await mountPage()

    expect(replace).toHaveBeenCalledWith({ name: 'Dashboard' }) // replace: Back does not return to Home
    expect(wrapper.find('[data-test="cycle-dialog"]').exists()).toBe(false) // no cycle to ask
    expect(setCycle).not.toHaveBeenCalled()
    expect(resumePass).not.toHaveBeenCalled()
    expect(startPass).not.toHaveBeenCalled()
  })

  it('stays on Home when no pass is active', async () => {
    await mountPage()

    expect(replace).not.toHaveBeenCalled()
  })

  it('asks in the opening dialog whether to resume the paused pass of the month or start a new one', async () => {
    startPass.mockResolvedValue(undefined)
    const wrapper = await mountPage()
    const dialogChoice = () => wrapper.find('[data-test="cycle-dialog"] [data-test="pass-choice"]')

    // October has a paused production pass: resuming it is offered and selected first
    expect(dialogChoice().text()).toContain('pppp1111')
    expect(dialogChoice().find('[role="radio"][value="pppp1111"]').attributes('data-state')).toBe('checked')
    // September has none: no choice in the dialog
    await pickMonth(wrapper, '2026-09')
    expect(dialogChoice().exists()).toBe(false)
    await pickMonth(wrapper, '2026-10')

    await dialogChoice().find('[role="radio"][value="new"]').trigger('click')
    await closeCycleDialog(wrapper)
    expect(wrapper.find('[data-test="pass-choice"] [role="radio"][value="new"]').attributes('data-state')).toBe('checked') // kept on the page
    await startButton(wrapper).trigger('click')
    await flushPromises()
    expect(startPass).toHaveBeenCalledWith(false, ['v1', 'v2', 'v3'])
    expect(resumePass).not.toHaveBeenCalled()
  })

  it('asks the mode before the cycle, and offers only the paused passes of the mode chosen', async () => {
    setMode.mockImplementation(async (testMode: boolean) => {
      getCheckpoints.mockResolvedValue(checkpoints({ test_mode: testMode }))
      return testMode
    })
    const wrapper = await mountPage()
    const dialog = () => wrapper.find('[data-test="cycle-dialog"]')

    const html = dialog().html()
    expect(html.indexOf('aria-label="Test mode"')).toBeGreaterThan(-1)
    expect(html.indexOf('aria-label="Test mode"')).toBeLessThan(html.indexOf('data-test="cycle-picker"')) // mode first
    expect(dialog().text()).toContain('pppp1111')

    await dialog().findAll('[data-test="mode-btn"]').find(b => b.text() === 'YES')!.trigger('click')
    await flushPromises()
    expect(setMode).toHaveBeenCalledWith(true, undefined)
    expect(dialog().text()).toContain('tttt2222') // the test pass of the month
    expect(dialog().text()).not.toContain('pppp1111') // never the production one
  })

  it('lets the user switch their own mode while a job runs: it changes nothing shared', async () => {
    getCheckpoints.mockResolvedValue(checkpoints({ lock: { job_id: null, task: 'a job of the other mode', acquired_at: 't' } }))
    const wrapper = await mountPage()

    const buttons = wrapper.findAll('[data-test="cycle-dialog"] [data-test="mode-btn"]')
    expect(buttons).toHaveLength(2)
    for (const button of buttons) expect(button.attributes('disabled')).toBeUndefined()
  })

  it('starts on the current month even when the server targets another one', async () => {
    getCheckpoints.mockResolvedValue(checkpoints({ cycle: '202608' }))
    setCycle.mockResolvedValue(undefined)
    startPass.mockResolvedValue(undefined)
    const wrapper = await mountPage()

    await closeCycleDialog(wrapper)
    await wrapper.find('[role="radio"][value="new"]').trigger('click') // October has a paused pass
    await startButton(wrapper).trigger('click')
    await flushPromises()
    expect(setCycle).toHaveBeenCalledWith('202610')
  })
})
