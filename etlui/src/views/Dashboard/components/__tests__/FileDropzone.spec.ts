import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import FileDropzone from '@/views/Dashboard/components/FileDropzone.vue'

const props = { label: 'config.json', description: 'Parameters', accept: '.json', defaultFile: { filename: 'config_malaria.json', size: 795 } }

describe('FileDropzone', () => {
  it('shows the server file above the dropzone and hides the default while it exists', () => {
    const wrapper = mount(FileDropzone, { props: { ...props, serverFile: { exists: true, size: 2048 } } })
    const rows = wrapper.findAll('.file-input > div').map(d => d.classes())
    expect(rows[0]).toContain('status-row')
    expect(rows[1]).toContain('dropzone')
    expect(wrapper.find('.status-row').findAll('button').map(b => b.text())).toEqual(['Preview', 'Delete'])
    expect(wrapper.find('.default-status').exists()).toBe(false)
  })

  it('offers the default when nothing is on the server', () => {
    const wrapper = mount(FileDropzone, { props: { ...props, serverFile: { exists: false } } })
    expect(wrapper.find('.default-status').text()).toContain('config_malaria.json')
  })
})
