import { describe, it, expect } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import HelpView from '@/views/Help/HelpView.vue'
import { HELP } from '@/views/Help/content'

const terms = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('[data-test="glossary"] dt').map(t => t.text())

describe('HelpView', () => {
  it('explains the flow and defines the app\'s words', () => {
    const wrapper = mount(HelpView)

    expect(wrapper.findAll('[data-test="how-it-works"] li').length).toBeGreaterThan(5)
    for (const word of ['Cycle', 'Pass', 'Run', 'Step', 'Item', 'Job', 'Journal', 'Logs']) expect(terms(wrapper)).toContain(word)
    expect(terms(wrapper)).toEqual([...terms(wrapper)].sort()) // alphabetical, to find a word quickly
    const pass = wrapper.find('[data-test="pass-help"]').text()
    for (const action of ['Pause the cycle', 'Abandon the cycle', 'Resume paused pass', 'Resume']) expect(pass).toContain(action)
  })

  it('switches to French and remembers the choice', async () => {
    const wrapper = mount(HelpView)

    await wrapper.find('[data-test="help-lang"] [value="fr"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('h3').text()).toBe('Fonctionnement')
    expect(terms(wrapper)).toContain('Step (étape)')
    expect(localStorage.getItem('etlui-help-lang')).toBe('fr')
    expect(mount(HelpView).find('h3').text()).toBe('Fonctionnement') // read back on the next visit
  })

  it('defines the same words, with the same anchors, in both languages', () => {
    expect(HELP.fr.glossary.map(g => g.id)).toEqual(HELP.en.glossary.map(g => g.id))
    expect(HELP.fr.how.length).toBe(HELP.en.how.length)
    expect(HELP.fr.steps.length).toBe(HELP.en.steps.length)
    expect(HELP.fr.pass.length).toBe(HELP.en.pass.length)
  })
})
