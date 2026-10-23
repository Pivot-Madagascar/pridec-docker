import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import BaseDialog from '@/views/Dashboard/components/BaseDialog.vue'

describe('BaseDialog', () => {
  it('puts the toasts back above the modal it opens', async () => {
    const layer = document.createElement('div')
    layer.setAttribute('data-toasts', '')
    const order: string[] = []
    Object.assign(layer, { hidePopover: vi.fn(() => order.push('hide')), showPopover: vi.fn(() => order.push('show')) })
    document.body.append(layer)
    const wrapper = mount(BaseDialog, { props: { open: false } })

    await wrapper.setProps({ open: true })
    await nextTick()

    expect(order).toEqual(['hide', 'show'])
    layer.remove()
  })
})
