import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const getCheckpoints = vi.fn()
vi.mock('@/services/pipeline', () => ({ getCheckpoints: (...args: unknown[]) => getCheckpoints(...args) }))

import ModeBadge from '@/components/ModeBadge.vue'
import { useAuthStore } from '@/stores/auth'
import { useModeStore } from '@/stores/mode'

const USER = { id: 'u1', email: null, username: 'tester', displayName: 'Tester' }
const badge = async () => {
  const wrapper = mount(ModeBadge)
  await flushPromises()
  return wrapper.find('[data-test="mode-badge"]')
}

describe('ModeBadge', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('shows test mode and DRYRUN as etlhub sends them, once logged in', async () => {
    useAuthStore().setUser(USER)
    getCheckpoints.mockResolvedValue({ test_mode: true, dry_run: true })

    expect((await badge()).text()).toBe('TEST MODE · DRYRUN')
  })

  it('warns that production writes to DHIS2', async () => {
    useAuthStore().setUser(USER)
    getCheckpoints.mockResolvedValue({ test_mode: false, dry_run: false })

    expect((await badge()).text()).toBe('PRODUCTION · DHIS2 writes')
  })

  it('follows a mode change made on a page, without reading etlhub again', async () => {
    useAuthStore().setUser(USER)
    getCheckpoints.mockResolvedValue({ test_mode: true, dry_run: true })
    const wrapper = mount(ModeBadge)
    await flushPromises()

    useModeStore().set({ test_mode: false, dry_run: false }) // what usePipeline does after PUT /pipeline/mode
    await flushPromises()

    expect(wrapper.find('[data-test="mode-badge"]').text()).toBe('PRODUCTION · DHIS2 writes')
    expect(getCheckpoints).toHaveBeenCalledTimes(1)
  })

  it('shows nothing and asks nothing when logged out, or when etlhub cannot answer', async () => {
    expect((await badge()).exists()).toBe(false)
    expect(getCheckpoints).not.toHaveBeenCalled()

    useAuthStore().setUser(USER)
    getCheckpoints.mockRejectedValue(new Error('down'))
    expect((await badge()).exists()).toBe(false)
  })
})
