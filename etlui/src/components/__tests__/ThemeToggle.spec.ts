import { describe, it, expect, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ThemeToggle from '@/components/ThemeToggle.vue'

const html = document.documentElement
const pick = async (wrapper: ReturnType<typeof mount>, label: string) => {
  await wrapper.find(`[aria-label="${label}"]`).trigger('click')
  await flushPromises()
}

describe('ThemeToggle', () => {
  beforeEach(() => {
    localStorage.clear()
    html.classList.remove('dark', 'light')
  })

  it('writes the chosen theme on <html> and remembers it', async () => {
    const wrapper = mount(ThemeToggle)
    await pick(wrapper, 'Dark theme')
    expect(html.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('etlui-theme')).toBe('dark')

    await pick(wrapper, 'Light theme')
    expect(html.classList.contains('dark')).toBe(false)
    expect(localStorage.getItem('etlui-theme')).toBe('light')

    await pick(wrapper, 'Light theme') // already active: stays light, never empty
    expect(localStorage.getItem('etlui-theme')).toBe('light')
    wrapper.unmount()
  })

  it('starts from the remembered choice', async () => {
    localStorage.setItem('etlui-theme', 'dark')
    const wrapper = mount(ThemeToggle)
    await flushPromises()
    expect(html.classList.contains('dark')).toBe(true)
    expect(wrapper.find('[aria-label="Dark theme"]').attributes('data-state')).toBe('on')
    wrapper.unmount()
  })
})
