import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const listRequests = vi.fn()
const getRequest = vi.fn()
const getJobLogs = vi.fn()
vi.mock('@/services/api', () => ({
  default: { defaults: { baseURL: 'http://localhost:8111' } },
  trackingApi: {
    listRequests: (...args: unknown[]) => listRequests(...args),
    getRequest: (...args: unknown[]) => getRequest(...args),
    getJobLogs: (...args: unknown[]) => getJobLogs(...args),
  },
}))

import TrackerView from '@/views/TrackerView/TrackerView.vue'

class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: ((e: { code: number; wasClean: boolean }) => void) | null = null
  closed = false
  constructor(public url: string) { FakeWebSocket.instances.push(this) }
  close() { this.closed = true }
  send(message: object) { this.onmessage!({ data: JSON.stringify(message) }) }
}

const row = (id: string, path: string, jobId: string | null = null) => ({
  request_id: id, timestamp: null, method: 'POST', url: `http://localhost:8111${path}`,
  status_code: 202, duration_ms: 3, client_host: null, error: null, job_id: jobId,
})

async function openDetail(wrapper: ReturnType<typeof mount>, request: ReturnType<typeof row>) {
  getRequest.mockResolvedValue({ data: request })
  await wrapper.find('tbody tr').trigger('click')
  await flushPromises()
}

describe('TrackerView', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.stubGlobal('WebSocket', FakeWebSocket)
    FakeWebSocket.instances = []
    listRequests.mockReset()
    getRequest.mockReset()
    getJobLogs.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('loads the last 50 requests once on mount, with no polling', async () => {
    listRequests.mockResolvedValue({ data: [row('a', '/import_gee')] })

    const wrapper = mount(TrackerView)
    await flushPromises()
    await vi.advanceTimersByTimeAsync(10000)

    expect(listRequests).toHaveBeenCalledTimes(1)
    expect(listRequests).toHaveBeenCalledWith(50, undefined)
    expect(wrapper.text()).toContain('/import_gee')
  })

  it('reloads with the filter on Refresh', async () => {
    listRequests.mockResolvedValue({ data: [] })
    const wrapper = mount(TrackerView)
    await flushPromises()

    await wrapper.find('input').setValue('/import_gee')
    expect(listRequests).toHaveBeenCalledTimes(1)  // typing alone does not reload
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(listRequests).toHaveBeenLastCalledWith(50, '/import_gee')
  })

  it('pages through the 50 loaded requests, 10 per page', async () => {
    listRequests.mockResolvedValue({ data: Array.from({ length: 50 }, (_, i) => row(`r${i}`, `/path${i}`)) })

    const wrapper = mount(TrackerView)
    await flushPromises()

    expect(wrapper.text()).toContain('Page 1 / 5')
    expect(wrapper.findAll('tbody tr')).toHaveLength(10)
  })

  it('shows the error when loading fails', async () => {
    listRequests.mockRejectedValue(new Error('Network Error'))

    const wrapper = mount(TrackerView)
    await flushPromises()

    expect(wrapper.text()).toContain('Network Error')
  })

  it('shows the request in one table row and its job logs in the same modal', async () => {
    const launch = row('a', '/import_gee', 'import_gee_1234abcd')
    listRequests.mockResolvedValue({ data: [launch] })
    getJobLogs.mockResolvedValue({ data: { job_id: 'import_gee_1234abcd', status: 'success', message: 'done', logs: 'step 1\nstep 2' } })
    const wrapper = mount(TrackerView)
    await flushPromises()

    await openDetail(wrapper, launch)

    expect(wrapper.findAll('.fixed th').map((th) => th.text())).toEqual(['Method', 'Status', 'URL', 'Duration', 'Job ID'])
    expect(wrapper.findAll('.fixed tbody tr')).toHaveLength(1)
    expect(getJobLogs).toHaveBeenCalledWith('import_gee_1234abcd')
    expect(wrapper.find('.job-logs-section').text()).toContain('step 1')
    expect(wrapper.text()).toContain('success')
  })

  it('offers no detail for a request that started no job', async () => {
    listRequests.mockResolvedValue({ data: [row('b', '/input/files')] })
    const wrapper = mount(TrackerView)
    await flushPromises()

    expect(wrapper.find('.detail-btn').exists()).toBe(false)
    await wrapper.find('tbody tr').trigger('click')
    await flushPromises()

    expect(getRequest).not.toHaveBeenCalled()
    expect(wrapper.text()).not.toContain('Request Detail')
  })

  it('explains when the job logs are gone', async () => {
    const launch = row('a', '/import_gee', 'import_gee_1234abcd')
    listRequests.mockResolvedValue({ data: [launch] })
    getJobLogs.mockRejectedValue({ response: { status: 404 } })
    const wrapper = mount(TrackerView)
    await flushPromises()

    await openDetail(wrapper, launch)

    expect(wrapper.text()).toContain('No logs found for this job')
  })

  it('follows a running job live over the WebSocket, then reloads its final state', async () => {
    const launch = row('a', '/import_gee', 'import_gee_1234abcd')
    listRequests.mockResolvedValue({ data: [launch] })
    getJobLogs.mockResolvedValue({ data: { job_id: 'import_gee_1234abcd', status: 'running', message: 'Starting', logs: null } })
    const wrapper = mount(TrackerView)
    await flushPromises()
    await openDetail(wrapper, launch)

    const socket = FakeWebSocket.instances[0]
    expect(socket.url).toBe('ws://localhost:8111/api/tracking/etl-logs/import_gee_1234abcd')
    expect(wrapper.find('.live-badge').exists()).toBe(true)

    socket.send({ type: 'etl_log_history', job_id: 'import_gee_1234abcd', logs: '' })
    socket.send({ type: 'etl_log_entry', job_id: 'import_gee_1234abcd', message: 'fetching GEE' })
    await flushPromises()
    expect(wrapper.text()).toContain('fetching GEE')

    getJobLogs.mockResolvedValue({ data: { job_id: 'import_gee_1234abcd', status: 'success', message: 'GEE import completed', logs: 'fetching GEE\ndone' } })
    socket.send({ type: 'job_status_update', job_id: 'import_gee_1234abcd', status: 'success' })
    await flushPromises()

    expect(getJobLogs).toHaveBeenCalledTimes(2)
    expect(socket.closed).toBe(true)
    expect(wrapper.find('.live-badge').exists()).toBe(false)
    expect(wrapper.text()).toContain('GEE import completed')
  })

  it('does not open a WebSocket for a finished job', async () => {
    const launch = row('a', '/import_gee', 'import_gee_1234abcd')
    listRequests.mockResolvedValue({ data: [launch] })
    getJobLogs.mockResolvedValue({ data: { job_id: 'import_gee_1234abcd', status: 'success', message: null, logs: 'done' } })
    const wrapper = mount(TrackerView)
    await flushPromises()
    await openDetail(wrapper, launch)

    expect(FakeWebSocket.instances).toHaveLength(0)
  })

  it('closes the WebSocket when the detail modal is closed', async () => {
    const launch = row('a', '/import_gee', 'import_gee_1234abcd')
    listRequests.mockResolvedValue({ data: [launch] })
    getJobLogs.mockResolvedValue({ data: { job_id: 'import_gee_1234abcd', status: 'pending', message: 'Queued', logs: null } })
    const wrapper = mount(TrackerView)
    await flushPromises()
    await openDetail(wrapper, launch)

    await wrapper.findAll('button').find((b) => b.text() === 'Close')!.trigger('click')

    expect(FakeWebSocket.instances[0].closed).toBe(true)
    expect(wrapper.find('.live-badge').exists()).toBe(false)
  })

  it('shows why the pipeline refused a request, though it started no job', async () => {
    const refused = { ...row('r', '/build_analytics'), status_code: 409, reason: 'build_analytics needs step data_import done first' }
    listRequests.mockResolvedValue({ data: [refused] })
    const wrapper = mount(TrackerView)
    await flushPromises()

    await openDetail(wrapper, refused)

    expect(wrapper.text()).toContain('Refused by the pipeline: build_analytics needs step data_import done first')
    expect(getJobLogs).not.toHaveBeenCalled()
  })
})
