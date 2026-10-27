import { describe, it, expect } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h, ref } from 'vue'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'

// A pointerdown outside a modal closes it, except on the toasts (App.vue's [data-toasts] layer).
const mountOpen = async () => {
  const open = ref(true)
  const wrapper = mount(defineComponent({
    setup: () => () => h(Dialog, { open: open.value, 'onUpdate:open': (v: boolean) => (open.value = v) }, () =>
      h(DialogContent, { 'aria-describedby': undefined }, () => h(DialogTitle, () => 'Title')))
  }), { attachTo: document.body })
  await flushPromises()
  await new Promise(r => setTimeout(r, 0)) // Reka listens for outside pointerdowns a tick after opening
  return { open, wrapper }
}

const pointerDownOn = async (el: Element) => {
  el.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }))
  el.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }))
  el.dispatchEvent(new MouseEvent('click', { bubbles: true }))
  await flushPromises()
}

describe('DialogContent', () => {
  it('stays open when a toast is clicked, closes on any other outside click', async () => {
    const toasts = document.createElement('div')
    toasts.setAttribute('data-toasts', '')
    const toast = toasts.appendChild(document.createElement('button'))
    const elsewhere = document.createElement('button')
    document.body.append(toasts, elsewhere)
    const { open, wrapper } = await mountOpen()

    await pointerDownOn(toast)
    expect(open.value).toBe(true)
    await pointerDownOn(elsewhere)
    expect(open.value).toBe(false)

    wrapper.unmount()
    toasts.remove()
    elsewhere.remove()
  })

  it('puts the dialog opened last on top, whatever the mount order', async () => {
    const first = ref(false)
    const second = ref(false)
    const dialog = (open: typeof first, title: string) => h(Dialog, { open: open.value }, () =>
      h(DialogContent, { 'aria-describedby': undefined, 'data-test': title }, () => h(DialogTitle, () => title)))
    const wrapper = mount(defineComponent({ setup: () => () => h('div', [dialog(first, 'mounted-first'), dialog(second, 'mounted-second')]) }))
    second.value = true
    await flushPromises()
    first.value = true // opened from the second one, like a preview from the Steps dialog
    await flushPromises()

    const z = (name: string) => Number((wrapper.find(`[data-test="${name}"]`).element as HTMLElement).style.zIndex)
    expect(z('mounted-first')).toBeGreaterThan(z('mounted-second'))
    wrapper.unmount()
  })
})
