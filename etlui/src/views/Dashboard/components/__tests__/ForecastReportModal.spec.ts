import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ForecastReportModal from '../ForecastReportModal.vue'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: '<p>report</p>' }),
    getUri: ({ url }: { url: string }) => `http://api${url}`,
  },
}))

const archiveLink = (run: { source: string; disease: string } | null) =>
  mount(ForecastReportModal, { props: { modelValue: true, run } }).find('a[download]')

describe('ForecastReportModal', () => {
  it('offers the input/ and output/ zip of the open run next to Refresh', async () => {
    const link = archiveLink(null)
    await flushPromises()

    expect(link.attributes('href')).toBe('http://api/output/archive')
    expect(link.attributes('target')).toBe('_blank')
  })

  it('hides it for a closed run, whose files are no longer in input/', () => {
    expect(archiveLink({ source: 'csb', disease: 'Malaria' }).exists()).toBe(false)
  })
})
