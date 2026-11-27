import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const getJobLogs = vi.fn()
const getRequest = vi.fn()
vi.mock('@/services/api', () => ({
  default: { defaults: { baseURL: 'http://localhost:8111' } },
  trackingApi: {
    getJobLogs: (...args: unknown[]) => getJobLogs(...args),
    getRequest: (...args: unknown[]) => getRequest(...args),
  },
}))

import RecentActivity from '@/views/Dashboard/components/RecentActivity.vue'

const REQUEST = { request_id: 'req-1', timestamp: null, method: 'POST', url: 'http://localhost:8111/import_gee',
  status_code: 202, duration_ms: 12.5, client_host: null, job_id: 'import_gee_1234abcd', error: null }

const entry = (id: number, jobId: string | null = null, request: typeof REQUEST | null = null, success = true) =>
  ({ id: String(id), action: 'Import GEE', message: 'started', time: '2026-11-25 10:00', success, jobId, request })
// A shadcn Trace line per entry: folded, its details (message, Detail button) shown once unfolded.
const unfold = async (wrapper: ReturnType<typeof mount>, index = 0) => {
  await wrapper.findAll('[data-test="activity-entry"] button')[index].trigger('click')
  await flushPromises()
}

describe('RecentActivity', () => {
  beforeEach(() => {
    getJobLogs.mockReset()
    getRequest.mockReset()
  })

  it('opens the journal\'s request and the job logs from the Detail button, like the tracking page', async () => {
    getJobLogs.mockResolvedValue({ data: { job_id: 'import_gee_1234abcd', status: 'success', message: 'done', logs: 'step 1' } })
    const wrapper = mount(RecentActivity, { props: { activityLog: [entry(1, 'import_gee_1234abcd', REQUEST), entry(2)] } })

    expect(wrapper.find('[data-test="detail-btn"]').exists()).toBe(false) // folded
    await unfold(wrapper, 0)
    await unfold(wrapper, 1)
    expect(wrapper.findAll('[data-test="detail-btn"]')).toHaveLength(1) // only an entry with a request or a job
    await wrapper.find('[data-test="detail-btn"]').trigger('click')
    await flushPromises()

    expect(getRequest).not.toHaveBeenCalled() // the journal already joined the request
    expect(wrapper.text()).toContain('/import_gee')
    expect(wrapper.text()).toContain('202')
    expect(getJobLogs).toHaveBeenCalledWith('import_gee_1234abcd')
    expect(wrapper.find('[data-test="job-logs-section"]').text()).toContain('step 1')

    await wrapper.findAll('button').find((b) => b.text() === 'Close')!.trigger('click')
    expect(wrapper.find('[data-test="job-logs-section"]').exists()).toBe(false)
  })

  it('is shown even with no activity, with a hint and a link to all the requests', () => {
    const wrapper = mount(RecentActivity, {
      props: { activityLog: [] },
      global: { stubs: { RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' } } }
    })

    expect(wrapper.find('[data-slot="card-title"]').text()).toBe('Recent Activity')
    expect(wrapper.text()).toContain('No activity yet')
    expect(wrapper.find('[data-slot="card-action"] a').attributes('href')).toBe('/tracking') // "View all"
  })

  it('shows each entry with the colour and icon of its status, and its message once unfolded', async () => {
    const wrapper = mount(RecentActivity, { props: { activityLog: [entry(1), { ...entry(2, 'import_gee_1', null, false), message: 'DHIS2 refused' }] } })

    const lines = wrapper.findAll('[data-slot="trace-line"]')
    expect(lines.map(l => l.attributes('data-status') ?? 'success')).toEqual(['success', 'error'])
    expect(lines[0].find('[data-test="status-success"]').exists()).toBe(true)
    expect(lines[1].find('[data-test="status-error"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('DHIS2 refused') // folded

    await unfold(wrapper, 1)
    expect(wrapper.text()).toContain('DHIS2 refused')
  })
})
