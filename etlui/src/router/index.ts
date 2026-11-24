import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useModeStore } from '@/stores/mode'
import { waitBetweenRoutes } from '@/router/loading'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: () => import('@/views/Home/HomeView.vue'),
      // label: the page title in App's top bar; title: the browser tab's.
      meta: { title: 'ETL UI - Start a pass', label: 'Start a pass' },
      // Home starts a pass: with one active in the user's mode, straight to the forecast page, Home never shown.
      // etlhub is asked each time (another user or tab may have started one); unknown (an error): Home, which says it.
      beforeEnter: async () => {
        const mode = useModeStore()
        await mode.load()
        return mode.passActive ? { name: 'Dashboard' } : true
      }
    },
    {
      path: '/forecast',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard/Dashboard.vue'),
      meta: { title: 'ETL UI - Dashboard', label: 'Forecast' }
    },
    {
      path: '/tracking',
      name: 'Tracking',
      component: () => import('@/views/TrackerView/TrackerView.vue'),
      meta: { title: 'Request Tracking', label: 'Tracking' }
    },
    {
      path: '/journal',
      name: 'Journal',
      component: () => import('@/views/Journal/JournalView.vue'),
      meta: { title: 'Cycle journal', label: 'Journal' }
    },
    {
      path: '/logs',
      name: 'ETLLogs',
      component: () => import('@/views/LogsStreamPage.vue'),
      meta: { title: 'ETL Logs Stream', label: 'Logs' }
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Auth/LoginForm.vue'),
      meta: { title: 'Login', public: true }
    },
    {
      path: '/parameters',
      name: 'Parameters',
      component: () => import('@/views/Parameters/ParametersView.vue'),
      meta: { title: 'Parameters', label: 'Parameters' }
    },
    // Merged into /parameters on 2026-11-23: old links open its Configuration section.
    { path: '/admin/config', redirect: { path: '/parameters', query: { section: 'configuration' } } }
  ]
})

router.beforeEach((to, _from, next) => {
  document.title = to.meta.title || 'ETL UI'
  
  const authStore = useAuthStore()
  const isPublic = to.meta.public === true
  const authenticated = authStore.isAuthenticated

  if (authenticated && to.name === 'Login') {
    next({ name: 'Dashboard' })
  } else if (!isPublic && !authenticated) {
    next({ name: 'Login' })
  } else {
    next()
  }
})

router.beforeResolve(waitBetweenRoutes) // ROUTE_LOADING_MS (500 ms) loading screen between two pages (App.vue)

export default router
