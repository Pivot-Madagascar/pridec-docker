import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const getJournal = vi.fn()
const getCycles = vi.fn()
vi.mock('@/services/pipeline', () => ({
  getJournal: (...args: unknown[]) => getJournal(...args),
  getCycles: (...args: unknown[]) => getCycles(...args),
  journalCsvUrl: (cycle: string) => `http://localhost:8111/pipeline/cycles/${cycle}/journal.csv`
}))
const query: { cycle?: string } = {}
const replace = vi.fn()
vi.mock('vue-router', () => ({ useRoute: () => ({ query }), useRouter: () => ({ replace }) }))
vi.mock('@/services/api', async importOriginal => ({
  ...(await importOriginal<object>()),
  trackingApi: { getJobLogs: vi.fn().mockResolvedValue({ data: { job_id: 'x', status: 'success', message: null, logs: '' } }) }
}))

import JournalView from '@/views/Journal/JournalView.vue'
import { useAuthStore } from '@/stores/auth'

const event = (over: object) => ({
  cycle: '202610', at: '2026-10-16T09:00:00.000000', step: 'data_import', item: 'import_gee', event: 'launched',
  job_id: null, actor: 'jdoe', request_id: null, detail: null, mode: 'production', request: null, ...over
})
const REQUEST = {
  request_id: 'r1', timestamp: null, method: 'POST', url: 'http://localhost:8111/import_gee', status_code: 202,
  duration_ms: 3, client_host: null, error: null, job_id: null
}

const CYCLES = [
  { cycle: '202611', state: 'open', test_state: 'open', target: true, events: 0, test_events: 2, last_at: null },
  { cycle: '202610', state: 'closed', test_state: null, target: false, events: 42, test_events: 3, last_at: '2026-10-31T17:45:00.000000' },
  { cycle: '202512', state: 'open', test_state: null, target: false, events: 5, test_events: 0, last_at: null }
]

describe('JournalView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getCycles.mockResolvedValue(CYCLES)
    query.cycle = '202610'
  })

  it('lists the cycles and shows the journal of the one clicked', async () => {
    getJournal.mockResolvedValue([])
    const wrapper = mount(JournalView)
    await flushPromises()

    const years = wrapper.findAll('nav details')
    expect(years.map(d => [d.find('summary').text(), d.attributes('open') !== undefined])).toEqual([['2026', true], ['2025', false]])
    const cards = wrapper.findAll('nav button')
    expect(cards).toHaveLength(3)
    expect(cards[0].text()).toContain('launches go here')
    expect(cards[0].text()).toContain('test: open')
    expect(cards[1].text()).toContain('complete')
    expect(cards[1].text()).toContain('42 events')
    expect(cards[1].text()).toContain('+3 test')
    expect(cards[1].text()).not.toContain('test: ')
    expect(cards[1].attributes('aria-current')).toBe('true') // ?cycle=202610

    await cards[0].trigger('click')
    expect(getJournal).toHaveBeenLastCalledWith('202611')
    expect(replace).toHaveBeenCalledWith({ query: { cycle: '202611' } })
  })

  it('opens the target cycle without ?cycle=', async () => {
    delete query.cycle
    getJournal.mockResolvedValue([])
    mount(JournalView)
    await flushPromises()

    expect(getJournal).toHaveBeenCalledWith('202611')
  })

  it('shows the events of the cycle in the link, test ones marked, and filters by mode', async () => {
    getJournal.mockResolvedValue([
      event({ detail: { confirm: true } }),
      event({ item: 'import_pivot_com', event: 'succeeded', actor: 'worker', mode: 'test' })
    ])
    const wrapper = mount(JournalView)
    await flushPromises()

    expect(getJournal).toHaveBeenCalledWith('202610')
    const rows = wrapper.findAll('tbody tr')
    expect(rows).toHaveLength(2)
    expect(rows[0].text()).toContain('confirm: true')
    expect(rows[1].text()).toContain('test')

    await wrapper.find('select[aria-label="Mode"]').setValue('production')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
  })

  it('offers the CSV export to administrators only', async () => {
    getJournal.mockResolvedValue([])
    expect(mount(JournalView).find('a[download]').exists()).toBe(false)
    await flushPromises()

    useAuthStore().setUser({ id: '1', email: null, username: 'admin', displayName: null, is_admin: true })
    const link = mount(JournalView).find('a[download]')
    expect(link.attributes('href')).toBe('http://localhost:8111/pipeline/cycles/202610/journal.csv')
  })

  it('opens the request that caused an event', async () => {
    getJournal.mockResolvedValue([event({ request_id: 'r1', request: REQUEST })])
    const wrapper = mount(JournalView)
    await flushPromises()

    await wrapper.find('tbody tr').trigger('click')

    expect(wrapper.text()).toContain('http://localhost:8111/import_gee')
  })
})
