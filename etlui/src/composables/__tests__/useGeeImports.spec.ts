import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick, ref } from 'vue'
import { flushPromises } from '@vue/test-utils'

const getGeeImports = vi.fn()
vi.mock('@/services/pipeline', () => ({ getGeeImports: () => getGeeImports() }))

import { useGeeImports } from '@/composables/useGeeImports'
import type { Checkpoints } from '@/types/pipeline'

const VARIABLES = [{ variable: 'v1', chosen: true, state: null }]
const checkpoints = (status: string) => ({
  cycle: '202611', test_mode: true, pass: { id: 'p1' },
  steps: [{ step: 'data_import', done: false, accessible: true, items: [{ item: 'import_gee', status, job_id: 'j', updated_at: null, launchable: true }] }]
}) as unknown as Checkpoints

describe('useGeeImports', () => {
  beforeEach(() => {
    getGeeImports.mockReset()
    getGeeImports.mockResolvedValue(VARIABLES)
  })

  it('reads the variables when the dialog opens, then at each new pipeline state while it is open', async () => {
    const state = ref<Checkpoints | null>(checkpoints('pending'))
    const gee = useGeeImports(state)

    state.value = checkpoints('pending') // closed: nothing read
    await nextTick()
    expect(getGeeImports).not.toHaveBeenCalled()

    gee.show()
    await flushPromises()
    expect(gee.open.value).toBe(true)
    expect(gee.variables.value).toEqual(VARIABLES)
    expect(getGeeImports).toHaveBeenCalledTimes(1)

    state.value = checkpoints('running') // launched: its lines change while it runs
    await flushPromises()
    state.value = checkpoints('running') // the next poll (usePipeline, every 3 s while the lock is held)
    await flushPromises()
    state.value = checkpoints('error') // its end: the last states
    await flushPromises()
    expect(getGeeImports).toHaveBeenCalledTimes(4)

    gee.close()
    state.value = checkpoints('running')
    await flushPromises()
    expect(getGeeImports).toHaveBeenCalledTimes(4)
  })

  it('keeps the error of a failed read', async () => {
    getGeeImports.mockRejectedValue(new Error('Network Error'))
    const gee = useGeeImports(ref(checkpoints('pending')))

    gee.show()
    await flushPromises()

    expect(gee.error.value).toBe('Could not read the GEE variables')
    expect(gee.loading.value).toBe(false)
  })
})
