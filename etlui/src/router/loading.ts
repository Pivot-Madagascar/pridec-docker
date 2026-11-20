import { computed, ref } from 'vue'
import { START_LOCATION, type RouteLocationNormalized } from 'vue-router'

export const ROUTE_LOADING_MS = 1000

const waiting = ref(0) // a counter: a navigation cancelled by a newer one must not hide the newer one's screen
export const routeLoading = computed(() => waiting.value > 0)

let skipNext = false
// For a caller that already showed its own loading screen (Dashboard: pause or abandon, then Home).
export const skipNextRouteLoading = () => { skipNext = true }

// beforeResolve: runs once per navigation that lands, after the auth guard's redirects.
// Not on the first load, nor when only the query or hash changes (same route).
export async function waitBetweenRoutes(to: RouteLocationNormalized, from: RouteLocationNormalized) {
  const skip = skipNext
  skipNext = false
  if (skip || from === START_LOCATION || to.name === from.name) return
  waiting.value++
  try {
    await new Promise(resolve => setTimeout(resolve, ROUTE_LOADING_MS))
  } finally {
    waiting.value--
  }
}
