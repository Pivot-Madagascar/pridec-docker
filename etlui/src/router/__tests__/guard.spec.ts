import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const USER = { id: '123', email: 'test@example.com', username: 'test', displayName: 'Test User' }

describe('Router Guard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('should redirect unauthenticated users to Login for protected routes', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [
        {
          path: '/',
          name: 'Landing',
          component: () => ({ template: '<div>Landing</div>' }),
          meta: { title: 'Landing' }
        },
        {
          path: '/tracking',
          name: 'Tracking',
          component: () => ({ template: '<div>Tracking</div>' }),
          meta: { title: 'Tracking' }
        },
        {
          path: '/login',
          name: 'Login',
          component: () => ({ template: '<div>Login</div>' }),
          meta: { title: 'Login', public: true }
        },
        {
          path: '/parameters',
          name: 'Parameters',
          component: () => ({ template: '<div>Parameters</div>' }),
          meta: { title: 'Parameters' }
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

    await router.push('/tracking')
    await router.isReady()

expect(router.currentRoute.value.name).toBe('Login')
   })

   it('should redirect unauthenticated users to Login for dashboard route', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', name: 'Landing', component: () => ({ template: '<div>Landing</div>' }), meta: { title: 'Landing' } },
        { path: '/login', name: 'Login', component: () => ({ template: '<div>Login</div>' }), meta: { public: true } },
      ]
    })

    router.beforeEach((to, _from, next) => {
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

    await router.push('/')
    await router.isReady()

    expect(router.currentRoute.value.name).toBe('Login')
  })

   it('should redirect authenticated users to Landing when accessing Login', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', name: 'Landing', component: () => ({ template: '<div>Landing</div>' }), meta: { title: 'Landing' } },
        { path: '/tracking', name: 'Tracking', component: () => ({ template: '<div>Tracking</div>' }) },
        { path: '/login', name: 'Login', component: () => ({ template: '<div>Login</div>' }), meta: { title: 'Login', public: true } },
      ]
    })

    const authStore = useAuthStore()
    authStore.setUser(USER)

    router.beforeEach((to, _from, next) => {
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

    await router.push('/login')
    await router.isReady()

    expect(router.currentRoute.value.name).toBe('Landing')
  })

  it('should allow authenticated users to access protected routes', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', name: 'Landing', component: () => ({ template: '<div>Landing</div>' }), meta: { title: 'Landing' } },
        { path: '/tracking', name: 'Tracking', component: () => ({ template: '<div>Tracking</div>' }) },
        { path: '/login', name: 'Login', component: () => ({ template: '<div>Login</div>' }), meta: { public: true } },
      ]
    })

    const authStore = useAuthStore()
    authStore.setUser(USER)

    router.beforeEach((to, _from, next) => {
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

    await router.push('/tracking')
    await router.isReady()

    expect(router.currentRoute.value.name).toBe('Tracking')
  })
})

describe('Auth Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('should be unauthenticated when no user in localStorage', () => {
    const authStore = useAuthStore()
    expect(authStore.isAuthenticated).toBe(false)
  })

  it('should be authenticated when a user is set, and keep no token', () => {
    const authStore = useAuthStore()
    authStore.setUser(USER)
    expect(authStore.isAuthenticated).toBe(true)
    expect(JSON.parse(localStorage.getItem('user')!)).toEqual(USER)
    expect(localStorage.getItem('token')).toBe(null)
  })

  it('should be unauthenticated after clear(), and drop a token left by the old login', () => {
    localStorage.setItem('token', 'old-token')
    const authStore = useAuthStore()
    authStore.setUser(USER)
    authStore.clear()
    expect(authStore.isAuthenticated).toBe(false)
    expect(localStorage.getItem('user')).toBe(null)
    expect(localStorage.getItem('token')).toBe(null)
  })

  it('should restore the user from localStorage', () => {
    localStorage.setItem('user', JSON.stringify(USER))
    const authStore = useAuthStore()
    expect(authStore.user).toEqual(USER)
    expect(authStore.isAuthenticated).toBe(true)
  })
})
