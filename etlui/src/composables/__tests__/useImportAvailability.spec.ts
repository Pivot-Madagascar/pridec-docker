import { describe, it, expect, vi, beforeEach } from 'vitest'

const getImportAvailability = vi.fn()
vi.mock('@/services/pipeline', () => ({ getImportAvailability: (...args: unknown[]) => getImportAvailability(...args) }))

import { useImportAvailability } from '@/composables/useImportAvailability'

describe('useImportAvailability', () => {
  beforeEach(() => vi.clearAllMocks())

  it('opens at once with the loader, then holds the report', async () => {
    let answer!: (v: unknown) => void
    getImportAvailability.mockReturnValue(new Promise(resolve => (answer = resolve)))
    const { show, open, loading, report } = useImportAvailability()

    const shown = show()
    expect([open.value, loading.value]).toEqual([true, true])
    answer({ imports: [] })
    await shown

    expect([loading.value, report.value]).toEqual([false, { imports: [] }])
  })

  it('asks etlhub at each opening (etlhub decides what it reuses), and Refresh forces a new check', async () => {
    getImportAvailability.mockResolvedValue({ imports: [] })
    const { show, close, load } = useImportAvailability()

    await show()
    close()
    await show()
    await load(true)

    expect(getImportAvailability.mock.calls).toEqual([[false], [false], [true]])
  })

  it("drops the answer of a check closed meanwhile", async () => {
    let answer!: (v: unknown) => void
    getImportAvailability.mockReturnValue(new Promise(resolve => (answer = resolve)))
    const { show, close, report, loading } = useImportAvailability()

    const shown = show()
    close()
    answer({ imports: [] })
    await shown

    expect([report.value, loading.value]).toEqual([null, false])
  })

  it("shows etlhub's message when the check cannot run", async () => {
    getImportAvailability.mockRejectedValue({ response: { data: { message: 'Import availability check failed: no session' } } })
    const { show, error, report } = useImportAvailability()

    await show()

    expect([error.value, report.value]).toEqual(['Import availability check failed: no session', null])
  })
})
