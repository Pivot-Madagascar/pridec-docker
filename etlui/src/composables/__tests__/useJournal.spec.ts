import { describe, it, expect, vi, beforeEach } from 'vitest'

const getJournal = vi.fn()
const getCycles = vi.fn()
const getCheckpoints = vi.fn()
const releaseLock = vi.fn()
vi.mock('@/services/pipeline', () => ({
  getJournal: (...args: unknown[]) => getJournal(...args),
  getCycles: (...args: unknown[]) => getCycles(...args),
  getCheckpoints: (...args: unknown[]) => getCheckpoints(...args),
  releaseLock: (...args: unknown[]) => releaseLock(...args),
  journalCsvUrl: (cycle: string) => `csv/${cycle}`
}))

import { useJournal } from '@/composables/useJournal'

describe('useJournal', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads the events of a cycle', async () => {
    getJournal.mockResolvedValue([{ event: 'launched' }])
    const { load, events, loading, error } = useJournal()

    await load('202610')

    expect(getJournal).toHaveBeenCalledWith('202610')
    expect(events.value).toEqual([{ event: 'launched' }])
    expect([loading.value, error.value]).toEqual([false, ''])
  })

  it('keeps only the answer of the last cycle asked', async () => {
    let first!: (v: unknown) => void
    getJournal.mockReturnValueOnce(new Promise(resolve => (first = resolve))).mockResolvedValueOnce([{ event: 'b' }])
    const { load, events } = useJournal()

    const slow = load('202609')
    await load('202610')
    first([{ event: 'a' }])
    await slow

    expect(events.value).toEqual([{ event: 'b' }])
  })

  it('shows the error and no stale events', async () => {
    getJournal.mockResolvedValueOnce([{ event: 'a' }]).mockRejectedValueOnce({ response: { data: { detail: 'Not Found' } } })
    const { load, events, error } = useJournal()

    await load('202610')
    await load('202611')

    expect(events.value).toEqual([])
    expect(error.value).toBe('Not Found')
  })

  it('loads the cycles, and shows why when it cannot', async () => {
    getCycles.mockResolvedValueOnce([{ cycle: '202610' }]).mockRejectedValueOnce({ response: { data: { detail: 'boom' } } })
    const { loadCycles, cycles, error } = useJournal()

    await loadCycles()
    expect(cycles.value).toEqual([{ cycle: '202610' }])

    await loadCycles()
    expect(error.value).toBe('boom')
  })

  it('reads the job lock, releases it, then reloads the lock and the journal', async () => {
    const LOCK = { job_id: 'forecast_1a2b3c4d', task: 'forecast', acquired_at: '2026-10-28T09:00:00' }
    getCheckpoints.mockResolvedValueOnce({ lock: LOCK }).mockResolvedValueOnce({ lock: null })
    getCycles.mockResolvedValue([])
    getJournal.mockResolvedValue([])
    releaseLock.mockResolvedValue('forecast_1a2b3c4d')
    const { loadLock, releaseLock: release, lock } = useJournal()

    await loadLock()
    expect(lock.value).toEqual(LOCK)

    await release('cccc3333')
    expect(releaseLock).toHaveBeenCalledTimes(1)
    expect(getJournal).toHaveBeenCalledWith('cccc3333') // its lock_released event shows
    expect(lock.value).toBeNull()
  })
})
