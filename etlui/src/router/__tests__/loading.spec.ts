import { describe, it, expect, vi, afterEach } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { ROUTE_LOADING_MS, routeLoading, skipNextRouteLoading, waitBetweenRoutes } from '@/router/loading'

const page = { template: '<div />' }
const makeRouter = () => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', name: 'Home', component: page }, { path: '/journal', name: 'Journal', component: page }]
  })
  router.beforeResolve(waitBetweenRoutes)
  return router
}

describe('waitBetweenRoutes', () => {
  afterEach(() => vi.useRealTimers())

  it('shows the loading screen ROUTE_LOADING_MS between two pages, not on the first load nor on a query change', async () => {
    vi.useFakeTimers()
    const router = makeRouter()
    await router.push('/') // first load: no wait
    expect(router.currentRoute.value.name).toBe('Home')

    const going = router.push('/journal')
    await vi.advanceTimersByTimeAsync(ROUTE_LOADING_MS - 1)
    expect(routeLoading.value).toBe(true)
    expect(router.currentRoute.value.name).toBe('Home')
    await vi.advanceTimersByTimeAsync(1)
    await going
    expect(routeLoading.value).toBe(false)
    expect(router.currentRoute.value.name).toBe('Journal')

    await router.push('/journal?pass=1') // same page
    expect(router.currentRoute.value.query.pass).toBe('1')
    expect(routeLoading.value).toBe(false)
  })

  it('skips the next wait when the caller showed its own screen', async () => {
    vi.useFakeTimers()
    const router = makeRouter()
    await router.push('/')
    skipNextRouteLoading()
    await router.push('/journal')
    expect(router.currentRoute.value.name).toBe('Journal')
    expect(routeLoading.value).toBe(false)
  })
})
