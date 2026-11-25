import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const getJournal = vi.fn()
vi.mock('@/services/pipeline', () => ({ getJournal: (...args: unknown[]) => getJournal(...args) }))

import { toActivity, usePassActivity, RECENT } from '@/composables/usePassActivity'
import type { Checkpoints, JournalEvent } from '@/types/pipeline'

const request = (id: string, status = 200) => ({ request_id: id, timestamp: null, method: 'POST', url: `/x/${id}`, status_code: status,
  duration_ms: 1, client_host: null, job_id: null, error: null })
const event = (event: string, requestId: string | null, extra: Partial<JournalEvent> = {}): JournalEvent => ({
  cycle: '202610', pass_id: 'p1', at: '2026-11-25T09:19:42.123456', step: 'forecast', item: null, event, job_id: null,
  actor: 'jdoe', request_id: requestId, detail: null, mode: 'test', request: requestId ? request(requestId) : null, ...extra
})

describe('toActivity', () => {
  it('keeps the pass\'s last requests, newest first, one line each, reads and worker events left out', () => {
    const events = [
      event('pass_started', 'r0'),
      ...Array.from({ length: 6 }, (_, i) => event('uploaded', `r${i + 1}`, { item: 'config/Malaria' })),
      event('availability_checked', 'r8'), // a read: not the pass's work
      event('succeeded', 'r9', { item: 'COM/Malaria:fetch_climate', job_id: 'fetch_climate_1' }),
      event('cycle_closed', null) // no request
    ]
    const entries = toActivity(events)

    expect(entries).toHaveLength(RECENT)
    expect(entries.map(e => e.request?.request_id)).toEqual(['r9', 'r6', 'r5', 'r4', 'r3', 'r2'])
    expect(entries[0]).toMatchObject({
      action: 'Climate data', message: 'Completed · Malaria · Community sites (COM) · by jdoe',
      time: '2026-11-25 09:19', success: true, jobId: 'fetch_climate_1'
    })
  })

  it('shows a failed job or a refused request as a failure, a request once even with several events', () => {
    const entries = toActivity([
      event('run_opened', 'r1'), event('reset', 'r1'), // one request, two events: its newest
      event('failed', 'r2', { item: 'COM/Malaria:forecast', job_id: 'forecast_1' }),
      { ...event('removed', 'r3'), request: request('r3', 409) }
    ])
    expect(entries.map(e => [e.action, e.success])).toEqual([['File removed', false], ['Forecast computation', false], ['Reset', true]])
  })
})

describe('usePassActivity', () => {
  beforeEach(() => vi.clearAllMocks())

  it('reads the journal of the pass shown at each new state, and empties without a pass', async () => {
    getJournal.mockResolvedValue([event('uploaded', 'r1', { item: 'config/Malaria' })])
    const state = ref<Checkpoints | null>(null)
    const { activity, error } = usePassActivity(state)

    state.value = { pass: { id: 'p1' } } as Checkpoints
    await flushPromises()
    expect(getJournal).toHaveBeenCalledWith('p1')
    expect(activity.value.map(e => e.action)).toEqual(['Parameters (config.json)'])

    getJournal.mockRejectedValueOnce(new Error('down'))
    state.value = { pass: { id: 'p1' } } as Checkpoints // the next state (a poll, an action's end)
    await flushPromises()
    expect(activity.value).toHaveLength(1) // kept
    expect(error.value).not.toBe('')

    state.value = { pass: null } as unknown as Checkpoints
    await flushPromises()
    expect(activity.value).toEqual([])
  })
})
