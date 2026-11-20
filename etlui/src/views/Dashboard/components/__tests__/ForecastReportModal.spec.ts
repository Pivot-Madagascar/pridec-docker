import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ForecastReportModal from '../ForecastReportModal.vue'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: '<p>report</p>' }),
    getUri: ({ url }: { url: string }) => `http://api${url}`,
  },
}))

// The dialog content renders a tick after mount (portal): wait for it before looking.
const archiveLink = async (run: { source: string; disease: string } | null) => {
  const wrapper = mount(ForecastReportModal, { props: { modelValue: true, run } })
  await flushPromises()
  expect(wrapper.find('iframe').exists()).toBe(true) // the content is there
  return wrapper.find('a[download]')
}

describe('ForecastReportModal', () => {
  it('offers the input/ and output/ zip of the open run next to Refresh', async () => {
    const link = await archiveLink(null)

    expect(link.attributes('href')).toBe('http://api/output/archive')
    expect(link.attributes('target')).toBe('_blank')
  })

  it('hides it for a closed run, whose files are no longer in input/', async () => {
    expect((await archiveLink({ source: 'csb', disease: 'Malaria' })).exists()).toBe(false)
  })
})
