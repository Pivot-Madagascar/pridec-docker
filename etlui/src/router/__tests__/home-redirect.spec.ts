import { describe, it, expect, vi, beforeEach } from 'vitest'

const getCheckpoints = vi.fn()
vi.mock('@/services/pipeline', () => ({ getCheckpoints: () => getCheckpoints() }))
vi.mock('@/views/Home/HomeView.vue', () => ({ default: { render: () => null } }))
vi.mock('@/views/Dashboard/Dashboard.vue', () => ({ default: { render: () => null } }))

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
    expect(getCheckpoints).toHaveBeenCalledTimes(2)
  })

  it('opens Home when etlhub cannot answer (Home shows the error)', async () => {
    await go('/journal')
    getCheckpoints.mockRejectedValue(new Error('down'))
    expect(await go('/')).toBe('Home')
  })
})
