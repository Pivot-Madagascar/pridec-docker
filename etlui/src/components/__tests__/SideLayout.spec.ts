import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SideLayout from '@/components/SideLayout.vue'

describe('SideLayout', () => {
  it('puts the side slot in the side panel, the page beside it', () => {
    const wrapper = mount(SideLayout, { slots: { side: '<p>panel</p>', default: '<main>page</main>' } })

    expect(wrapper.find('aside [data-slot="scroll-area"] p').text()).toBe('panel') // in a shadcn ScrollArea
    expect(wrapper.find('aside main').exists()).toBe(false)
    expect(wrapper.find('main').text()).toBe('page')
  })

  it('has no panel without a side slot (Tracking): the page alone, at the same place', () => {
    const wrapper = mount(SideLayout, { slots: { default: '<main>page</main>' } })

    expect(wrapper.find('aside').exists()).toBe(false)
    expect(wrapper.find('main').text()).toBe('page')
  })
})
