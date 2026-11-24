import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

const logout = vi.fn()
vi.mock('@/services/auth', () => ({ logout: () => logout() }))
vi.mock('@/services/pipeline', () => ({ getCheckpoints: vi.fn().mockResolvedValue({ test_mode: true, dry_run: true }) }))
vi.mock('vue3-hot-toast', () => ({ Toaster: { render: () => null } }))

import App from '@/App.vue'
import { getCheckpoints } from '@/services/pipeline'
import { useAuthStore } from '@/stores/auth'

const page = { template: '<p data-test="page">page</p>' }
const mountAt = async (path: string) => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: page, meta: { label: 'Start a pass' } },
      { path: '/journal', component: page, meta: { label: 'Journal' } },
      { path: '/login', component: page, meta: { public: true } }
    ]
  })
  await router.push(path)
  const wrapper = mount(App, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    useAuthStore().setUser({ id: 'u1', email: null, username: 'tester', displayName: 'Tester' })
  })

  it('shows the side menu, the page title and the user in the top bar', async () => {
    const wrapper = await mountAt('/journal')

    const entries = wrapper.findAll('[data-test="nav-item"]').map(a => a.text())
    expect(entries).toEqual(['Start a pass', 'Forecast', 'Journal', 'Tracking', 'Logs', 'Parameters'])
    expect(wrapper.find('[data-test="nav-item"][data-active="true"]').text()).toBe('Journal')
    expect(wrapper.find('header h1').text()).toBe('Journal')
    expect(wrapper.find('[data-test="user-name"]').text()).toBe('Tester')
    expect(wrapper.find('[data-test="page"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('hides Start a pass while the user\'s mode has an active pass', async () => {
    vi.mocked(getCheckpoints).mockResolvedValueOnce({ test_mode: true, dry_run: true, pass: { state: 'active' } } as never)
    const wrapper = await mountAt('/journal')

    const entries = wrapper.findAll('[data-test="nav-item"]').map(a => a.text())
    expect(entries).toEqual(['Forecast', 'Journal', 'Tracking', 'Logs', 'Parameters'])
    wrapper.unmount()
  })

  it('logs out from the bottom of the side menu', async () => {
    const wrapper = await mountAt('/')

    await wrapper.find('[data-sidebar="footer"] [data-test="logout"]').trigger('click')
    expect(logout).toHaveBeenCalledOnce() // through the auth store (no service in App)
    wrapper.unmount()
  })

  it('links to the help page from the bottom of the side menu', async () => {
    const wrapper = await mountAt('/')

    expect(wrapper.find('[data-sidebar="footer"] [data-test="help-link"]').attributes('href')).toBe('/help')
    wrapper.unmount()
  })

  it('shows the login page alone, without the menu', async () => {
    useAuthStore().setUser(null)
    const wrapper = await mountAt('/login')

    expect(wrapper.find('[data-test="page"]').exists()).toBe(true)
    expect(wrapper.find('[data-slot="sidebar-wrapper"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="logout"]').exists()).toBe(false)
    wrapper.unmount()
  })
})
