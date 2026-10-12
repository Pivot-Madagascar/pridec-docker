import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

const getCheckpoints = vi.fn()
const launchJob = vi.fn()
const setMode = vi.fn()
const getInputFiles = vi.fn()
const showNotification = vi.fn()
const addActivity = vi.fn()
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
  uploadInputFile: vi.fn(),
  deleteInputFile: vi.fn()
}))
vi.mock('@/composables/useNotification', () => ({ useNotification: () => ({ showNotification }) }))

import { usePipeline, POLL_MS } from '@/composables/usePipeline'

const STATE = { cycle: '202610', lock: null, dry_run: false, steps: [] }
const LOCKED = { ...STATE, lock: { job_id: 'import_gee_1', task: 'import_gee', acquired_at: 't' } }
const conflict = (data: object) => ({ response: { status: 409, data } })

describe('usePipeline', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getInputFiles.mockResolvedValue({})
    getCheckpoints.mockResolvedValue(STATE)
  })
  afterEach(() => vi.useRealTimers())

  it('launches, notifies and reads the state again from the server', async () => {
    launchJob.mockResolvedValue('import_gee_1')
    const { launch, state } = usePipeline(addActivity)

    expect(await launch('import_gee', 'Import GEE')).toBe(true)

    expect(launchJob).toHaveBeenCalledWith('import_gee', false)
    expect(showNotification).toHaveBeenCalledWith('Import GEE: accepted', 'success')
    expect(state.value).toEqual(STATE)
  })

  it('shows the message of a 409 and does not retry', async () => {
    launchJob.mockRejectedValue(conflict({ message: 'build_analytics needs data_import/import_gee in success first' }))
    const { launch, pending } = usePipeline(addActivity)

    expect(await launch('build_analytics', 'Build Analytics')).toBe(false)

    expect(showNotification).toHaveBeenCalledWith('build_analytics needs data_import/import_gee in success first', 'error')
    expect(pending.value).toBeNull()
    expect(launchJob).toHaveBeenCalledTimes(1)
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
    setMode.mockRejectedValue(conflict({ code: 'confirmation_required', message: 'Leaving test mode…', impact: { mode: 'dry_run' } }))
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
