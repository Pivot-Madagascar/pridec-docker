import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const getJobLogs = vi.fn()
vi.mock('@/services/api', () => ({
  default: { defaults: { baseURL: 'http://localhost:8111' } },
  trackingApi: { getJobLogs: (...args: unknown[]) => getJobLogs(...args) },
}))

import RecentActivity from '@/views/Dashboard/components/RecentActivity.vue'

const entry = (id: number, jobId?: string) => ({ id, action: 'Import GEE', message: 'started', time: '10:00', success: true, jobId })

describe('RecentActivity', () => {
  beforeEach(() => getJobLogs.mockReset())

  it('opens the job logs from the Detail button of an activity that started a job', async () => {
    getJobLogs.mockResolvedValue({ data: { job_id: 'import_gee_1234abcd', status: 'success', message: 'done', logs: 'step 1' } })
    const wrapper = mount(RecentActivity, { props: { activityLog: [entry(1, 'import_gee_1234abcd'), entry(2)] } })

    expect(wrapper.findAll('.detail-btn')).toHaveLength(1)
    await wrapper.find('.detail-btn').trigger('click')
    await flushPromises()

    expect(getJobLogs).toHaveBeenCalledWith('import_gee_1234abcd')
    expect(wrapper.find('.job-logs-section').text()).toContain('step 1')

    await wrapper.findAll('button').find((b) => b.text() === 'Close')!.trigger('click')
    expect(wrapper.find('.job-logs-section').exists()).toBe(false)
  })
})
