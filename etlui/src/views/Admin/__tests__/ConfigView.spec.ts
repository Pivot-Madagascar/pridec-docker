import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const { config, update } = vi.hoisted(() => {
  const config = {
    dhis_url: 'https://dhis2.example', has_dhis_token: true, dhis_token_expires_at: null, parent_ou: 'OU_PARENT',
    ou_level: 5, disease_code: 'MAL', log_level: 'INFO', gee_variables: ['v1', 'v2']
  }
  return { config, update: vi.fn().mockResolvedValue(config) }
})
vi.mock('@/services/config', () => ({
  configService: { get: vi.fn().mockResolvedValue(config), update: (...args: unknown[]) => update(...args), reload: vi.fn() }
}))

import ConfigView from '@/views/Admin/ConfigView.vue'

describe('ConfigView', () => {
  it('lists the GEE variables of pridec_gee read only, and never sends them', async () => {
    const wrapper = mount(ConfigView)
    await flushPromises()

    const gee = wrapper.find('[data-test="gee-variables"]')
    expect(gee.findAll('li').map(li => li.text())).toEqual(['v1', 'v2'])
    expect(gee.find('input').exists()).toBe(false)

    await wrapper.findAll('button').find(b => b.text() === 'Save')!.trigger('click')
    await flushPromises()
    expect(update).toHaveBeenCalledWith({ parent_ou: 'OU_PARENT', ou_level: 5, disease_code: 'MAL', log_level: 'INFO' })
  })
})
