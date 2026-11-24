import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const { route, replace, connect, disconnect, clearLogs } = vi.hoisted(() => ({
  route: { query: {} as Record<string, string> },
  replace: vi.fn(),
  connect: vi.fn(),
  disconnect: vi.fn(),
  clearLogs: vi.fn()
}))
vi.mock('vue-router', async () => {
  const { reactive } = await import('vue')
  const current = reactive(route)
  replace.mockImplementation(({ query }: { query: Record<string, string> }) => { current.query = query })
  return { useRoute: () => current, useRouter: () => ({ replace }) }
})
vi.mock('@/composables/useWebSocketLogger', () => ({
  useWebSocketLogger: () => ({
    logs: ref([]), history: ref(''), status: ref(''), statusMessage: ref(''), connected: ref(false), connectionError: ref(''),
    connect, disconnect, clearLogs, isRunning: ref(false), isCompleted: ref(false), combinedLogs: ref('')
  })
}))

import LogsStreamPage from '@/views/LogsStreamPage.vue'

describe('LogsStreamPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('follows the job of ?jobId= at once (a toast\'s link), switches to another one, and Reset frees the input', async () => {
    route.query = { jobId: 'import_gee_1' }
    const wrapper = mount(LogsStreamPage)

    expect(connect).toHaveBeenCalledWith('import_gee_1')
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('import_gee_1')

    await replace({ query: { jobId: 'forecast_2' } }) // another toast's link while here
    await flushPromises()
    expect(clearLogs).toHaveBeenCalled() // the previous job's lines go
    expect(connect).toHaveBeenLastCalledWith('forecast_2')

    await wrapper.findAll('button').find(b => b.text() === 'Reset')!.trigger('click')
    await flushPromises()
    expect(replace).toHaveBeenLastCalledWith({ query: {} })
    expect(wrapper.find('input').attributes('disabled')).toBeUndefined()
  })
})
