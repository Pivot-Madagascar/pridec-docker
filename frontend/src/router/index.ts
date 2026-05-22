// router/index.ts
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/views/HomePage.vue'),
      meta: { hideLayout: true, title: 'Home' }
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { hideLayout: true, title: 'Login' }
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/Register.vue'),
      meta: { hideLayout: true, title: 'Register' }
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard.vue'),
      meta: { title: 'Dashboard' }
    },
    {
      path: '/data-fetch',
      name: 'DataFetch',
      component: () => import('@/views/DataFetch.vue'),
      meta: { title: 'Data Fetch' }
    },
    {
      path: '/forecasting',
      name: 'Forecasting',
      component: () => import('@/views/Forecasting.vue'),
      meta: { title: 'Forecasting' }
    },
    {
      path: '/forecast-post',
      name: 'ForecastPost',
      component: () => import('@/views/ForecastPost.vue'),
      meta: { title: 'ForecastPost' }
    },
    {
      path: '/reports',
      name: 'Reports',
      component: () => import('@/views/Reports.vue'),
      meta: { title: 'Reports' }
    },
    {
      path: '/history',
      name: 'History',
      component: () => import('@/views/History.vue'),
      meta: { title: 'History' }
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/views/NotFound.vue'),
      meta: { title: 'Page Not Found' }
    }
  ]
})

// Navigation guard for authentication (optional)
router.beforeEach((to, from, next) => {
  // Check if user is authenticated for protected routes
  const token = localStorage.getItem('token')
  const isAuthRoute = to.path === '/' || to.path === '/login' || to.path === '/register'
  const isProtectedRoute = !isAuthRoute

  if (isProtectedRoute && !token) {
    // Redirect to login if trying to access protected route without token
    next('/login')
  } else if (isAuthRoute && token) {
    // Redirect to dashboard if already authenticated and trying to access auth pages
    next('/dashboard')
  } else {
    next()
  }
})

export default router