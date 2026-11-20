import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const getFetchedImports = vi.fn()
vi.mock('@/services/pipeline', () => ({ getFetchedImports: (...args: unknown[]) => getFetchedImports(...args) }))

import { useFetchedImports } from '@/composables/useFetchedImports'
import { useFetchedImportsStore } from '@/stores/fetchedImports'
import type { Checkpoints } from '@/types/pipeline'

function checkpoints(comStatus: string, comJob: string, testMode = false): Checkpoints {
  const item = (name: string, status: string, job: string | null) =>
    ({ item: name, status, job_id: job, updated_at: null, launchable: true })
  return {
    cycle: '202611', current_step: 'data_import', run: null, lock: null, test_mode: testMode, dry_run: true,
    pass: { id: 'p1' }, steps: [{ step: 'data_import', done: false, accessible: true, items: [
      item('import_pivot_com', comStatus, comJob), item('import_pivot_csb', 'pending', null), item('approve_imports', 'pending', null)
    ] }]
  } as unknown as Checkpoints
}
const DATA = [{ task: 'import_pivot_com', elements: [] }]

describe('useFetchedImports', () => {
  beforeEach(() => {
    getFetchedImports.mockReset().mockResolvedValue(DATA)
  })

  it('keeps the answer in Pinia: read again only when an import finishes, the mode changes, or on Refresh', async () => {
    const state = ref<Checkpoints | null>(checkpoints('success', 'job1'))
    const fetched = useFetchedImports(state)

    fetched.show()
    await flushPromises()
    expect(getFetchedImports).toHaveBeenCalledTimes(1)
    expect(useFetchedImportsStore().imports).toEqual(DATA)

    fetched.close()
    fetched.show() // reopened: what was read
    await flushPromises()
    expect(getFetchedImports).toHaveBeenCalledTimes(1)

    state.value = checkpoints('running', 'job2') // relaunched: its files are being replaced
    await flushPromises()
    expect(getFetchedImports).toHaveBeenCalledTimes(1)
    state.value = checkpoints('success', 'job2') // finished: read again, dialog closed or not
    await flushPromises()
    expect(getFetchedImports).toHaveBeenCalledTimes(2)

    await fetched.refresh()
    expect(getFetchedImports).toHaveBeenCalledTimes(3)

    getFetchedImports.mockReturnValue(new Promise(() => {})) // the other mode's answer never comes
    state.value = checkpoints('success', 'job2', true)
    await flushPromises()
    expect(getFetchedImports).toHaveBeenCalledTimes(4)
    expect(fetched.imports.value).toBeNull() // the previous mode's data is never shown
  })

  it('reads nothing before the first show', async () => {
    const state = ref<Checkpoints | null>(checkpoints('success', 'job1'))
    useFetchedImports(state)
    state.value = checkpoints('success', 'job2')
    await flushPromises()
    expect(getFetchedImports).not.toHaveBeenCalled()
  })
})
