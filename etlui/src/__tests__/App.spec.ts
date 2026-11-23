import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const logout = vi.fn()
vi.mock('@/services/auth', () => ({ logout: () => logout() }))
vi.mock('@/services/pipeline', () => ({ getCheckpoints: vi.fn().mockResolvedValue({ test_mode: true, dry_run: true }) }))
vi.mock('vue3-hot-toast', () => ({ Toaster: { render: () => null } }))

import App from '@/App.vue'
import { useAuthStore } from '@/stores/auth'

const mountApp = async () => {
  const wrapper = mount(App, { global: { stubs: { RouterLink: { template: '<a><slot /></a>' }, RouterView: true } } })
  await wrapper.find('[aria-label="Open the menu"]').trigger('click')
  await flushPromises()
  return wrapper
}

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('logs out from the bottom of the side menu, once logged in', async () => {
    useAuthStore().setUser({ id: 'u1', email: null, username: 'tester', displayName: 'Tester' })
    const wrapper = await mountApp()

    const menu = wrapper.find('[data-test="drawer-footer"]')
    await menu.find('[data-test="logout"]').trigger('click')
    expect(logout).toHaveBeenCalledOnce() // through the auth store (no service in App)
    wrapper.unmount()
  })

  it('has no Log out when logged out', async () => {
    const wrapper = await mountApp()
    expect(wrapper.find('[data-test="logout"]').exists()).toBe(false)
    wrapper.unmount()
  })
})
