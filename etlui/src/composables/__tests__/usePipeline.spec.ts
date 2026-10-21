import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

const getCheckpoints = vi.fn()
const launchJob = vi.fn()
const setMode = vi.fn()
const getInputFiles = vi.fn()
const getDefaultFiles = vi.fn()
const applyDefaultFile = vi.fn()
const showNotification = vi.fn()
const addActivity = vi.fn()
const followJob = vi.fn()
vi.mock('@/services/pipeline', () => ({
  getCheckpoints: (...args: unknown[]) => getCheckpoints(...args),
  launchJob: (...args: unknown[]) => launchJob(...args),
  setMode: (...args: unknown[]) => setMode(...args),
  openRun: vi.fn(),
  abandonRun: vi.fn(),
  decideRun: vi.fn(),
  releaseLock: vi.fn()
}))
vi.mock('@/services/inputs', () => ({
  getInputFiles: (...args: unknown[]) => getInputFiles(...args),
  getDefaultFiles: (...args: unknown[]) => getDefaultFiles(...args),
  applyDefaultFile: (...args: unknown[]) => applyDefaultFile(...args),
  uploadInputFile: vi.fn(),
  deleteInputFile: vi.fn()
}))
vi.mock('@/composables/useNotification', () => ({ useNotification: () => ({ showNotification, followJob }) }))

import { usePipeline, POLL_MS } from '@/composables/usePipeline'

const STATE = { cycle: '202610', lock: null, test_mode: false, dry_run: true, steps: [] }
const LOCKED = { ...STATE, lock: { job_id: 'import_gee_1', task: 'import_gee', acquired_at: 't' } }
const conflict = (data: object) => ({ response: { status: 409, data } })

describe('usePipeline', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getInputFiles.mockResolvedValue({})
    getDefaultFiles.mockResolvedValue({})
    getCheckpoints.mockResolvedValue(STATE)
  })
  afterEach(() => vi.useRealTimers())

  it('reads the defaults with the state, and uses one with the confirmation rule of an upload', async () => {
    const DEFAULTS = { 'config/Malaria': { filename: 'config_malaria.json', size: 795 } }
    getDefaultFiles.mockResolvedValue(DEFAULTS)
    applyDefaultFile.mockRejectedValueOnce(conflict({ code: 'confirmation_required', message: 'used', impact: [] }))
    applyDefaultFile.mockResolvedValue('input/config.json')
    const { useDefault, defaults, pending, confirm } = usePipeline(addActivity)

    expect(await useDefault('config')).toBe(false)
    expect(defaults.value).toEqual(DEFAULTS)
    expect(pending.value?.label).toBe('Use the default config')

    expect(await confirm()).toBe(true)
    expect(applyDefaultFile.mock.calls).toEqual([['config', false], ['config', true]])
  })

  it('launches, follows the job in a toast, logs only its end and reads the state again', async () => {
    launchJob.mockResolvedValue({ jobId: 'import_gee_1', requestId: 'req-1' })
    let end!: (value: { success: boolean; message: string }) => void
    followJob.mockReturnValue(new Promise(resolve => { end = resolve }))
    const { launch, state } = usePipeline(addActivity)

    expect(await launch('import_gee', 'Import GEE')).toBe(true)

    expect(launchJob).toHaveBeenCalledWith('import_gee', false)
    expect(followJob).toHaveBeenCalledWith('Import GEE', 'import_gee_1')
    expect(showNotification).not.toHaveBeenCalled()
    expect(addActivity).not.toHaveBeenCalled() // the 202 is not an activity
    expect(state.value).toEqual(STATE)

    end({ success: false, message: 'boom' })
    await Promise.resolve()
    expect(addActivity).toHaveBeenCalledWith('Import GEE', 'boom', false, { jobId: 'import_gee_1', requestId: 'req-1' })
  })

  it('shows a 409 in plain words and does not retry', async () => {
    launchJob.mockRejectedValue(conflict({ message: 'build_analytics needs data_import/import_gee in success first' }))
    const { launch, pending } = usePipeline(addActivity)

    expect(await launch('build_analytics', 'Build Analytics')).toBe(false)

    expect(showNotification).toHaveBeenCalledWith('A previous step must be completed first.', 'error')
    expect(pending.value).toBeNull()
    expect(launchJob).toHaveBeenCalledTimes(1)

    launchJob.mockRejectedValue(conflict({ message: 'forecast (forecast_1) is running since t: one job at a time' }))
    await launch('forecast', 'Run Forecast')
    expect(showNotification).toHaveBeenLastCalledWith('A job is already running.', 'error')
  })

  it('keeps a confirmation_required until the user confirms, then resends with confirm=true', async () => {
    const impact = { item: 'import_gee', step: 'data_import', reset_items: [] }
    launchJob.mockRejectedValueOnce(conflict({ code: 'confirmation_required', message: 'import_gee is already in success', impact }))
    launchJob.mockResolvedValueOnce('import_gee_2')
    const { launch, pending, confirm } = usePipeline(addActivity)

    await launch('import_gee', 'Import GEE')
    expect(pending.value).toMatchObject({ label: 'Import GEE', impact })
    expect(showNotification).not.toHaveBeenCalledWith(expect.anything(), 'error')

    expect(await confirm()).toBe(true)
    expect(launchJob).toHaveBeenLastCalledWith('import_gee', true)
    expect(pending.value).toBeNull()
  })

  it('drops the action when the user cancels the confirmation', async () => {
    setMode.mockRejectedValue(conflict({ code: 'confirmation_required', message: 'Leaving test mode…', impact: { mode: 'test_mode' } }))
    const { setMode: switchMode, pending, cancel } = usePipeline(addActivity)

    await switchMode(false)
    cancel()

    expect(pending.value).toBeNull()
    expect(setMode).toHaveBeenCalledTimes(1)
  })

  it('reads the state again while a job holds the lock, and stops once it is free', async () => {
    vi.useFakeTimers()
    getCheckpoints.mockResolvedValueOnce(LOCKED).mockResolvedValueOnce(LOCKED).mockResolvedValue(STATE)
    const { refresh } = usePipeline(addActivity)

    await refresh()
    await vi.advanceTimersByTimeAsync(POLL_MS)
    await vi.advanceTimersByTimeAsync(POLL_MS)
    await vi.advanceTimersByTimeAsync(POLL_MS * 3)

    expect(getCheckpoints).toHaveBeenCalledTimes(3)
  })
})
