import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const { config, update, route } = vi.hoisted(() => {
  const config = {
    dhis_url: 'https://dhis2.example', has_dhis_token: true, dhis_token_expires_at: null, parent_ou: 'OU_PARENT',
    ou_level: 5, disease_code: 'MAL', log_level: 'INFO', gee_variables: ['v1', 'v2'],
    pivot_url: 'https://pivot.example', has_pivot_token: true
  }
  return { config, update: vi.fn().mockResolvedValue(config), route: { query: {} as Record<string, string> } }
})
vi.mock('@/services/config', () => ({
  configService: { get: vi.fn().mockResolvedValue(config), update: (...args: unknown[]) => update(...args), reload: vi.fn() }
}))
vi.mock('vue-router', async () => {
  const { reactive } = await import('vue')
  const current = reactive(route)
  return { useRoute: () => current, useRouter: () => ({ replace: ({ query }: { query: Record<string, string> }) => { current.query = query } }) }
})

import ParametersView from '@/views/Parameters/ParametersView.vue'
import { useAuthStore } from '@/stores/auth'

const mountPage = async (section?: string) => {
  route.query = section ? { section } : {}
  const wrapper = mount(ParametersView, { attachTo: document.body })
  await flushPromises()
  return wrapper
}
const tabs = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('[data-test="parameters-menu"] [role="tab"]')
const shown = (wrapper: ReturnType<typeof mount>) => wrapper.find('[role="tabpanel"][data-state="active"]')

describe('ParametersView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore().setUser({ id: 'u1', email: 'a@b.c', username: 'tester', displayName: 'Tester' })
  })

  it('shows one section at a time from a side menu, the profile first, and keeps the choice in the URL', async () => {
    const wrapper = await mountPage()

    expect(tabs(wrapper).map(t => t.text())).toEqual(['Profile', 'DHIS2', 'Configuration', 'GEE variables'])
    expect(shown(wrapper).text()).toContain('tester')
    await tabs(wrapper)[1].trigger('mousedown', { button: 0 })
    await flushPromises()
    expect(route.query).toEqual({ section: 'dhis2' })
    expect(shown(wrapper).text()).toContain('https://dhis2.example')
    wrapper.unmount()
  })

  it('opens the section of the URL (/admin/config redirects to configuration) and saves the editable keys only', async () => {
    const wrapper = await mountPage('configuration')

    await shown(wrapper).findAll('button').find(b => b.text() === 'Save')!.trigger('click')
    await flushPromises()
    expect(update).toHaveBeenCalledWith({
      parent_ou: 'OU_PARENT', ou_level: 5, disease_code: 'MAL', log_level: 'INFO', pivot_url: 'https://pivot.example'
    })
    expect(wrapper.find('[data-test="pivot-token"]').text()).toBe('Set in etlhub (.env)') // never the token
    wrapper.unmount()
  })

  it('lists the GEE variables of pridec_gee read only', async () => {
    const wrapper = await mountPage('gee')

    const gee = wrapper.find('[data-test="gee-variables"]')
    expect(gee.findAll('li').map(li => li.text())).toEqual(['v1', 'v2'])
    expect(gee.find('input').exists()).toBe(false)
    wrapper.unmount()
  })
})
