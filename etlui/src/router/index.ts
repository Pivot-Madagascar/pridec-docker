import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Landing',
      component: () => import('@/views/LandingPage.vue'),
      meta: { title: 'ETL UI - Dashboard' }
    },
    {
      path: '/forecast',
      name: 'Forecast',
      component: () => import('@/views/ForecastPage.vue'),
      meta: { title: 'Forecast' }
    },
    {
      path: '/tracking',
      name: 'Tracking',
      component: () => import('@/views/TrackerView.vue'),
      meta: { title: 'Request Tracking' }
    },
    {
      path: '/logs',
      name: 'ETLLogs',
      component: () => import('@/views/LogsStreamPage.vue'),
      meta: { title: 'ETL Logs Stream' }
    },
    {
      path: '/status/:jobId',
      name: 'JobStatus',
      component: () => import('@/views/JobStatus.vue'),
      meta: { title: 'Job Status' }
    }
  ]
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title || 'ETL UI'
  next()
})

export default router
