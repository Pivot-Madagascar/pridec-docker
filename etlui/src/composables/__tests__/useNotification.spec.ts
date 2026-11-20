import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick, type Component } from 'vue'

const { getJobLogs, toast } = vi.hoisted(() => ({
  getJobLogs: vi.fn(),
  toast: { loading: vi.fn(() => 'toast-1'), success: vi.fn(() => 'toast-2'), error: vi.fn(), dismiss: vi.fn() },
}))
vi.mock('vue3-hot-toast', () => ({ default: toast }))
vi.mock('@/services/api', () => ({ trackingApi: { getJobLogs: (...args: unknown[]) => getJobLogs(...args) } }))

import { useNotification, formatElapsed, JOB_POLL_MS, JOB_END_MS, LEAVE_MS } from '@/composables/useNotification'

const job = (status: string | null, message: string | null = null) => ({ data: { status, message } })
// What the toast shows: the component followJob handed to toast.loading, rendered.
const shown = () => mount(toast.loading.mock.calls[0][0] as unknown as Component)

describe('followJob', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(() => vi.useRealTimers())

  it('keeps every step in one toast, from accepted to running to completed, then lets it go after JOB_END_MS', async () => {
    vi.useFakeTimers()
    getJobLogs.mockResolvedValueOnce(job('pending')).mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce(job('running', 'Starting GEE import')).mockResolvedValueOnce(job('running'))
      .mockResolvedValueOnce(job('success', 'GEE import completed'))

    const ended = useNotification().followJob('Import GEE', 'import_gee_1')
    const wrapper = shown()
    expect(wrapper.text()).toContain('Import GEE')
    expect(wrapper.text()).toContain('Queued for a worker · import_gee_1')

    await vi.advanceTimersByTimeAsync(2 * JOB_POLL_MS)
    await nextTick()
    expect(wrapper.text()).toContain('Starting GEE import')

    await vi.advanceTimersByTimeAsync(2 * JOB_POLL_MS)
    expect(await ended).toEqual({ success: true, message: 'GEE import completed' })
    await nextTick()
    const text = wrapper.text()
    // The steps passed stay, in order, the running one with its elapsed time
    expect(text.indexOf('Accepted')).toBeLessThan(text.indexOf('Running'))
    expect(text.indexOf('Running')).toBeLessThan(text.indexOf('Completed'))
    expect(text).toContain('Starting GEE import · in progress for 9 s')
    expect(text).toContain('GEE import completed · 12 s')
    expect(toast.loading).toHaveBeenCalledTimes(1) // one toast, updated in place
    expect(toast.success).toHaveBeenCalledWith(toast.loading.mock.calls[0][0], { id: 'toast-1', duration: Infinity })
    await vi.advanceTimersByTimeAsync(JOB_END_MS)
    expect(toast.dismiss).toHaveBeenCalledWith('toast-1')
  })

  it('ends in error on an unknown job', async () => {
    getJobLogs.mockRejectedValueOnce({ response: { status: 404 } })

    expect(await useNotification().followJob('Run Forecast', 'forecast_1'))
      .toEqual({ success: false, message: 'Job not found on the server' })
    await nextTick()
    expect(shown().text()).toContain('Failed')
    expect(toast.error).toHaveBeenCalledWith(expect.anything(), { id: 'toast-1', duration: Infinity })
  })

  it('never closes a toast while the pointer is on the toasts, and closes it within LEAVE_MS once it leaves', async () => {
    vi.useFakeTimers()
    const hovered = vi.spyOn(document, 'querySelector').mockReturnValue(document.body) // [data-toasts]:hover matches
    useNotification().showNotification('Upload config: success', 'success')

    await vi.advanceTimersByTimeAsync(60_000)
    expect(toast.dismiss).not.toHaveBeenCalled()

    hovered.mockReturnValue(null)
    await vi.advanceTimersByTimeAsync(LEAVE_MS)
    hovered.mockRestore()
    expect(toast.dismiss).toHaveBeenCalledWith('toast-2')
  })

  it('formats an elapsed time for people', () => {
    expect([formatElapsed(42_000), formatElapsed(206_000), formatElapsed(3_900_000)]).toEqual(['42 s', '3 min 26 s', '1 h 05 min'])
  })
})
