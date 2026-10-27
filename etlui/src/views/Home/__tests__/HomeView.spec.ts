import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'

const getCheckpoints = vi.fn()
const getCycles = vi.fn()
const setCycle = vi.fn()
const resumePass = vi.fn()
vi.mock('@/services/pipeline', () => ({
  getCheckpoints: (...args: unknown[]) => getCheckpoints(...args),
  getCycles: (...args: unknown[]) => getCycles(...args),
  setCycle: (...args: unknown[]) => setCycle(...args),
  resumePass: (...args: unknown[]) => resumePass(...args),
  setMode: vi.fn(),
  journalCsvUrl: vi.fn()
}))
vi.mock('@/services/inputs', () => ({ getInputFiles: vi.fn().mockResolvedValue({}), getDefaultFiles: vi.fn().mockResolvedValue({}) }))
vi.mock('@/services/config', () => ({
  configService: {
    get: vi.fn().mockResolvedValue({
      dhis_url: 'https://dhis2.example', has_dhis_token: true, dhis_token_expires_at: null, parent_ou: 'OU_PARENT',
      ou_level: 5, disease_code: 'MAL', log_level: 'INFO', gee_variables: ''
    })
  }
}))
const push = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('vue3-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn(), loading: vi.fn(), dismiss: vi.fn() } }))

import HomeView from '@/views/Home/HomeView.vue'

const pass = (id: string, cycle: string, state: string, mode = 'production') => ({
  id, cycle, state, started_at: '2026-10-16T09:00:00.000000', started_by: 'jdoe', mode, events: 3, last_at: null
})
const checkpoints = (over: object = {}) => ({
  cycle: '202610', pass: null, current_step: null, run: null, lock: null, test_mode: false, dry_run: true, steps: [], ...over
})

let mounted: VueWrapper | null = null
async function mountPage() {
  const wrapper = (mounted = mount(HomeView, { attachTo: document.body })) // attached: the button submits the form
  await flushPromises()
  return wrapper
}
const startButton = (wrapper: Awaited<ReturnType<typeof mountPage>>) => wrapper.findAll('button').find(b => b.text() === 'Start')!

describe('HomeView', () => {
  afterEach(() => mounted?.unmount())

  beforeEach(() => {
    vi.clearAllMocks()
    getCheckpoints.mockResolvedValue(checkpoints())
    getCycles.mockResolvedValue([
      { cycle: '202610', target: true, passes: [pass('pppp1111', '202610', 'paused'), pass('tttt2222', '202610', 'paused', 'test')] },
      { cycle: '202609', target: false, passes: [pass('cccc3333', '202609', 'complete')] }
    ])
  })

  it('offers the paused pass of the chosen month and mode, resumes it and goes to the forecast page', async () => {
    resumePass.mockResolvedValue({})
    const wrapper = await mountPage()

    expect(wrapper.find<HTMLInputElement>('input[type="month"]').element.value).toBe('2026-10')
    expect(wrapper.text()).toContain('pppp1111')
    expect(wrapper.text()).not.toContain('tttt2222') // a test pass is not resumed in production
    expect(wrapper.find('[role="radio"][value="new"]').attributes('disabled')).toBeDefined()
    // The parameters of the pass
    expect(wrapper.text()).toContain('OU_PARENT')
    expect(wrapper.text()).toContain('https://dhis2.example')
    expect(wrapper.text()).toContain('DRYRUN on')

    await startButton(wrapper).trigger('click')
    await flushPromises()
    expect(resumePass).toHaveBeenCalledWith('pppp1111')
    expect(setCycle).not.toHaveBeenCalled()
    expect(push).toHaveBeenCalledWith({ name: 'Dashboard' })
  })

  it('starts a new pass on another month: sends the month, then goes to the forecast page', async () => {
    setCycle.mockResolvedValue(undefined)
    const wrapper = await mountPage()

    await wrapper.find('input[type="month"]').setValue('2026-09')
    expect(wrapper.text()).toContain('complete') // the redo is confirmed at the first launch
    await startButton(wrapper).trigger('click')
    await flushPromises()
    expect(setCycle).toHaveBeenCalledWith('202609')
    expect(resumePass).not.toHaveBeenCalled()
    expect(push).toHaveBeenCalledWith({ name: 'Dashboard' })
  })

  it('stays on the page when the server refuses', async () => {
    setCycle.mockRejectedValue({ response: { status: 409, data: { detail: 'A job is running' } } })
    const wrapper = await mountPage()

    await wrapper.find('input[type="month"]').setValue('2026-09')
    await startButton(wrapper).trigger('click')
    await flushPromises()
    expect(setCycle).toHaveBeenCalled()
    expect(push).not.toHaveBeenCalled()
  })

  it('continues an active pass: the month is locked and nothing is sent', async () => {
    getCheckpoints.mockResolvedValue(checkpoints({ pass: pass('aaaa4444', '202610', 'active') }))
    const wrapper = await mountPage()

    expect(wrapper.find('input[type="month"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('aaaa4444')
    await startButton(wrapper).trigger('click')
    await flushPromises()
    expect(setCycle).not.toHaveBeenCalled()
    expect(resumePass).not.toHaveBeenCalled()
    expect(push).toHaveBeenCalledWith({ name: 'Dashboard' })
  })
})
