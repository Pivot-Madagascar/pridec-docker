import { describe, it, expect, vi } from 'vitest'

const endSession = vi.fn()
vi.mock('@/services/auth', () => ({ logout: () => endSession() }))

import { useAuthStore } from '@/stores/auth'

describe('auth store logout', () => {
  it('ends the session, forgets the user and goes to /login, even if the request fails', async () => {
    const location = { href: '' } as Location
    const spy = vi.spyOn(window, 'location', 'get').mockReturnValue(location)
    const store = useAuthStore()
    store.setUser({ id: 'u1', email: null, username: 'admin', displayName: 'Admin' })
    endSession.mockRejectedValue(new Error('network'))

    await store.logout()

    expect(endSession).toHaveBeenCalledOnce()
    expect(store.isAuthenticated).toBe(false)
    expect(localStorage.getItem('user')).toBeNull()
    expect(location.href).toBe('/login')
    spy.mockRestore()
  })
})
