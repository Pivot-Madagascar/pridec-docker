import { describe, it, expect, vi, beforeEach } from 'vitest'

const getCheckpoints = vi.fn()
vi.mock('@/services/pipeline', () => ({ getCheckpoints: () => getCheckpoints() }))
vi.mock('@/views/Home/HomeView.vue', () => ({ default: { render: () => null } }))
vi.mock('@/views/Dashboard/Dashboard.vue', () => ({ default: { render: () => null } }))
vi.mock('@/views/TrackerView/TrackerView.vue', () => ({ default: { render: () => null } }))
vi.mock('@/views/LogsStreamPage.vue', () => ({ default: { render: () => null } }))

import router from '@/router'
import { skipNextRouteLoading } from '@/router/loading'
import { useAuthStore } from '@/stores/auth'

const pass = (state: string) => ({ test_mode: false, dry_run: false, pass: { id: 'p1', state } })
const go = async (path: string) => {
  skipNextRouteLoading() // not the short screen between pages
  await router.push(path)
  return router.currentRoute.value.name
}

describe('the route to Home', () => {
  beforeEach(() => {
    useAuthStore().setUser({ id: 'u1', email: null, username: 'tester', displayName: 'Tester' })
  })

  it('goes straight to the forecast page while a pass is active, asking etlhub each time', async () => {
    getCheckpoints.mockResolvedValue(pass('active'))
    expect(await go('/')).toBe('Dashboard') // Home never shows

    getCheckpoints.mockResolvedValue(pass('paused'))
    expect(await go('/')).toBe('Home')
    expect(getCheckpoints).toHaveBeenCalledTimes(3) // Home's route, then the forecast page's, then Home's
  })

  it('opens Home when etlhub cannot answer (Home shows the error)', async () => {
    await go('/journal')
    getCheckpoints.mockRejectedValue(new Error('down'))
    expect(await go('/')).toBe('Home')
  })
})

describe('the routes of an active pass (Forecast, Tracking, Logs)', () => {
  beforeEach(() => {
    useAuthStore().setUser({ id: 'u1', email: null, username: 'tester', displayName: 'Tester' })
  })

  it.each(['/forecast', '/tracking', '/logs'])('%s sends to Home without an active pass, opens with one', async path => {
    await go('/journal')
    for (const state of ['paused', 'complete', 'abandoned']) {
      getCheckpoints.mockResolvedValue(pass(state))
      expect(await go(path)).toBe('Home')
    }
    getCheckpoints.mockResolvedValue({ test_mode: true, dry_run: true, pass: null }) // never started
    expect(await go(path)).toBe('Home')
    getCheckpoints.mockRejectedValue(new Error('down')) // unknown: Home, which shows the error
    expect(await go(path)).toBe('Home')

    getCheckpoints.mockResolvedValue(pass('active'))
    expect(await go(path)).not.toBe('Home')
    expect(router.currentRoute.value.path).toBe(path)
  })
})
