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

const entry = (id: number, jobId?: string, requestId?: string) =>
  ({ id, action: 'Import GEE', message: 'started', time: '10:00', success: true, jobId, requestId })
const REQUEST = { request_id: 'req-1', timestamp: null, method: 'POST', url: 'http://localhost:8111/import_gee',
  status_code: 202, duration_ms: 12.5, client_host: null, job_id: 'import_gee_1234abcd', error: null }

describe('RecentActivity', () => {
  beforeEach(() => {
    getJobLogs.mockReset()
    getRequest.mockReset()
  })

  it('opens the tracked request and the job logs from the Detail button, like the tracking page', async () => {
    getJobLogs.mockResolvedValue({ data: { job_id: 'import_gee_1234abcd', status: 'success', message: 'done', logs: 'step 1' } })
    getRequest.mockResolvedValue({ data: REQUEST })
    const wrapper = mount(RecentActivity, { props: { activityLog: [entry(1, 'import_gee_1234abcd', 'req-1'), entry(2)] } })

    expect(wrapper.findAll('.detail-btn')).toHaveLength(1)
    await wrapper.find('.detail-btn').trigger('click')
    await flushPromises()

    expect(getRequest).toHaveBeenCalledWith('req-1')
    expect(wrapper.text()).toContain('/import_gee')
    expect(wrapper.text()).toContain('202')
    expect(getJobLogs).toHaveBeenCalledWith('import_gee_1234abcd')
    expect(wrapper.find('.job-logs-section').text()).toContain('step 1')

    await wrapper.findAll('button').find((b) => b.text() === 'Close')!.trigger('click')
    expect(wrapper.find('.job-logs-section').exists()).toBe(false)
  })
})
