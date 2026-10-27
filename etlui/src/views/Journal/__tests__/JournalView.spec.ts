import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const getJournal = vi.fn()
const getCycles = vi.fn()
const resumePass = vi.fn()
const abandonPass = vi.fn()
vi.mock('@/services/pipeline', () => ({
  getJournal: (...args: unknown[]) => getJournal(...args),
  getCycles: (...args: unknown[]) => getCycles(...args),
  resumePass: (...args: unknown[]) => resumePass(...args),
  abandonPass: (...args: unknown[]) => abandonPass(...args),
  journalCsvUrl: (passId: string) => `http://localhost:8111/pipeline/passes/${passId}/journal.csv`
}))
const query: { pass?: string } = {}
const replace = vi.fn()
vi.mock('vue-router', () => ({ useRoute: () => ({ query }), useRouter: () => ({ replace }) }))
vi.mock('@/services/api', async importOriginal => ({
  ...(await importOriginal<object>()),
  trackingApi: { getJobLogs: vi.fn().mockResolvedValue({ data: { job_id: 'x', status: 'success', message: null, logs: '' } }) }
}))

import JournalView from '@/views/Journal/JournalView.vue'
import { useAuthStore } from '@/stores/auth'

const event = (over: object) => ({
  cycle: '202610', pass_id: 'cccc3333', at: '2026-10-16T09:00:00.000000', step: 'data_import', item: 'import_gee', event: 'launched',
  job_id: null, actor: 'jdoe', request_id: null, detail: null, mode: 'production', request: null, ...over
})
const REQUEST = {
  request_id: 'r1', timestamp: null, method: 'POST', url: 'http://localhost:8111/import_gee', status_code: 202,
  duration_ms: 3, client_host: null, error: null, job_id: null
}

const pass = (id: string, cycle: string, over: object = {}) => ({
  id, cycle, state: 'complete', started_at: '2026-10-16T09:00:00.000000', started_by: 'jdoe', mode: 'production',
  events: 42, last_at: '2026-10-31T17:45:00.000000', ...over
})
const CYCLES = [
  { cycle: '202611', target: true, passes: [pass('aaaa1111', '202611', { state: 'active', mode: 'test', events: 2 })] },
  { cycle: '202610', target: false, passes: [pass('bbbb2222', '202610', { state: 'paused' }), pass('cccc3333', '202610')] },
  { cycle: '202512', target: false, passes: [pass('dddd4444', '202512', { state: 'abandoned', started_by: 'bob' })] }
]

describe('JournalView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear() // the table's rows per page and order are remembered
    getCycles.mockResolvedValue(CYCLES)
    query.pass = 'cccc3333'
  })

  it('lists the months with their passes and shows the journal of the pass clicked', async () => {
    getJournal.mockResolvedValue([])
    const wrapper = mount(JournalView)
    await flushPromises()

    const folds = (selector: string) =>
      wrapper.findAll(selector).map(d => [d.find('button').text(), d.attributes('data-state') === 'open'])
    expect(folds('[data-test="year"]')).toEqual([['2026', true], ['2025', false]])
    // A tree (shadcn file-tree look): each month folds its passes too, open for the target month and the selected pass's month
    const months = folds('[data-test="cycle"]')
    expect(months.map(([, open]) => open)).toEqual([true, true, false])
    expect(months[0][0]).toContain('launches go here')
    expect(months[1][0]).toContain('2 passes')
    const cards = wrapper.findAll('[data-test="pass"]') // one shadcn Trace line per pass, like Recent Activity
    expect(cards).toHaveLength(4)
    expect(cards[0].text()).toContain('active')
    expect(cards[0].text()).toContain('test')
    expect(cards[1].text()).toContain('paused')
    expect(cards[1].find('[data-test="state-paused"]').exists()).toBe(true) // the icon of its state
    expect(cards[1].find('dl').exists()).toBe(false) // folded: its details show once unfolded
    expect(cards[2].text()).toContain('complete')
    // The selected pass starts unfolded: its details as a labelled list, one fact per row
    const details = Object.fromEntries(cards[2].findAll('dt').map((dt, i) => [dt.text(), cards[2].findAll('dd')[i].text()]))
    expect(details).toMatchObject({ 'Started by': 'jdoe', Events: '42' })
    expect(Object.keys(details)).toEqual(['Started by', 'Started', 'Events', 'Last event'])
    expect(cards[2].find('button').attributes('aria-current')).toBe('true') // ?pass=cccc3333

    await cards[1].find('button').trigger('click') // selects the pass and unfolds its details
    await flushPromises()
    expect(cards[1].find('dl').text()).toContain('jdoe')
    expect(getJournal).toHaveBeenLastCalledWith('bbbb2222')
    expect(replace).toHaveBeenCalledWith({ query: { pass: 'bbbb2222' } })
  })

  it('opens the newest pass of the target month without ?pass=', async () => {
    delete query.pass
    getJournal.mockResolvedValue([])
    mount(JournalView)
    await flushPromises()

    expect(getJournal).toHaveBeenCalledWith('aaaa1111')
  })

  it('shows the events of the pass in the link, test ones marked, and filters by step', async () => {
    getJournal.mockResolvedValue([
      event({ detail: { confirm: true, dry_run: false, params: { task: 'import_gee' } } }),
      event({ step: 'forecast', item: 'COM/Malaria:forecast', event: 'succeeded', actor: 'worker', mode: 'test' })
    ])
    const wrapper = mount(JournalView)
    await flushPromises()

    expect(getJournal).toHaveBeenCalledWith('cccc3333')
    const rows = wrapper.findAll('tbody tr')
    expect(rows).toHaveLength(2) // newest first: etlhub sends them oldest first
    expect(rows[0].text()).toContain('test')
    expect(rows[1].text()).toContain('confirm: true · dry_run: false')
    expect(rows[1].text()).not.toContain('params') // an import's parameters: in the CSV only

    await wrapper.find('[data-test="order-btn"]').trigger('click')
    expect(wrapper.findAll('tbody tr')[0].text()).toContain('confirm: true')

    await wrapper.find('[aria-label="Step"]').trigger('keydown', { key: 'Enter' }) // shadcn Select: open, then pick
    await flushPromises()
    await wrapper.findAll('[role="option"]').find(o => o.text() === 'forecast')!.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
  })

  it("resumes a paused pass, and shows the server's refusal", async () => {
    query.pass = 'bbbb2222'
    getJournal.mockResolvedValue([])
    resumePass.mockRejectedValue({ response: { data: { message: 'Pass x is active: pause or abandon it first' } } })
    const wrapper = mount(JournalView)
    await flushPromises()

    await wrapper.findAll('button').find(b => b.text() === 'Resume')!.trigger('click')
    await flushPromises()
    expect(resumePass).toHaveBeenCalledWith('bbbb2222')
    expect(wrapper.text()).toContain('pause or abandon it first') // the server's refusal
  })

  it('abandons a paused pass after a confirmation; other passes have no buttons', async () => {
    query.pass = 'bbbb2222'
    getJournal.mockResolvedValue([])
    abandonPass.mockResolvedValue({})
    const wrapper = mount(JournalView, { attachTo: document.body })
    await flushPromises()

    await wrapper.findAll('button').find(b => b.text() === 'Abandon')!.trigger('click')
    expect(abandonPass).not.toHaveBeenCalled()
    await wrapper.findAll('[data-test="confirm-btn"]')[0].trigger('click')
    await flushPromises()
    expect(abandonPass).toHaveBeenCalledWith('bbbb2222')
    wrapper.unmount()

    query.pass = 'cccc3333'
    const complete = mount(JournalView)
    await flushPromises()
    expect(complete.findAll('button').filter(b => ['Resume', 'Abandon'].includes(b.text()))).toHaveLength(0) // the closed confirm dialog renders nothing
  })

  it('offers the CSV export to administrators only', async () => {
    getJournal.mockResolvedValue([])
    expect(mount(JournalView).find('a[download]').exists()).toBe(false)
    await flushPromises()

    useAuthStore().setUser({ id: '1', email: null, username: 'admin', displayName: null, is_admin: true })
    const link = mount(JournalView).find('a[download]')
    expect(link.attributes('href')).toBe('http://localhost:8111/pipeline/passes/cccc3333/journal.csv')
  })

  it('opens the request that caused an event', async () => {
    getJournal.mockResolvedValue([event({ request_id: 'r1', request: REQUEST })])
    const wrapper = mount(JournalView)
    await flushPromises()

    await wrapper.find('tbody tr').trigger('click')

    expect(wrapper.text()).toContain('http://localhost:8111/import_gee')
  })
})
