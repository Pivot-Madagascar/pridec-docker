import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Landing',
      component: () => import('@/views/LandingPage/LandingPage.vue'),
      meta: { title: 'ETL UI - Dashboard' }
    },
    {
      path: '/tracking',
      name: 'Tracking',
      component: () => import('@/views/TrackerView/TrackerView.vue'),
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
      component: () => import('@/views/Auth/ParametersPage.vue'),
      meta: { title: 'Parameters' }
    },
    {
      path: '/admin/config',
      name: 'AdminConfig',
      component: () => import('@/views/Admin/ConfigView.vue'),
      meta: { title: 'Admin Configuration' }
    }
  ]
})

router.beforeEach((to, _from, next) => {
  document.title = to.meta.title || 'ETL UI'
  
  const authStore = useAuthStore()
  const isPublic = to.meta.public === true
  const authenticated = authStore.isAuthenticated

  if (authenticated && to.name === 'Login') {
    next({ name: 'Landing' })
  } else if (!isPublic && !authenticated) {
    next({ name: 'Login' })
  } else {
    next()
  }
})

export default router