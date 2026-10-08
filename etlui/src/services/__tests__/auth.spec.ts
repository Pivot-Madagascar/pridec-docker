import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAuthStore } from '@/stores/auth'

const post = vi.fn()
vi.mock('@/services/api', () => ({
  default: { post: (...args: unknown[]) => post(...args) }
}))

import { login, logout } from '@/services/auth'

const USER = { id: 'u1', email: null, username: 'admin', displayName: 'Admin' }

describe('login', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('posts URL, username and password and keeps only the user', async () => {
    post.mockResolvedValue({ data: { user: USER, expires_at: 1 } })

    await login('https://dhis2.test', 'admin', 'pw')

    expect(post).toHaveBeenCalledWith('/auth/login', { dhis2_url: 'https://dhis2.test', username: 'admin', password: 'pw' })
    expect(useAuthStore().user).toEqual(USER)
    expect(JSON.stringify({ ...localStorage })).not.toContain('pw')
  })

  it.each([
    [400, 'not allowed'],
    [401, 'Invalid DHIS2 username or password'],
    [429, 'Too many failed attempts'],
    [502, 'unreachable'],
  ])('maps HTTP %i to a readable error', async (status, message) => {
    post.mockRejectedValue({ response: { status } })

    await expect(login('https://dhis2.test', 'admin', 'pw')).rejects.toThrow(message)
    expect(useAuthStore().isAuthenticated).toBe(false)
  })
})

describe('logout', () => {
  it('calls /auth/logout and clears the store even if the request fails', async () => {
    const assign = vi.spyOn(window, 'location', 'get').mockReturnValue({ href: '' } as Location)
    const store = useAuthStore()
    store.setUser(USER)
    post.mockRejectedValue(new Error('network'))

    await logout()

    expect(post).toHaveBeenCalledWith('/auth/logout')
    expect(store.isAuthenticated).toBe(false)
    assign.mockRestore()
  })
})
