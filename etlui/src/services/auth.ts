import api from './api'
import { useAuthStore } from '@/stores/auth'

const LOGIN_ERRORS: Record<number, string> = {
    400: 'This DHIS2 URL is not allowed',
    401: 'Invalid DHIS2 username or password',
    429: 'Too many failed attempts, try again later',
    502: 'DHIS2 is unreachable or returned an unexpected response',
    503: 'Session store unavailable, contact an administrator',
}

// etlhub exchanges the credentials for a DHIS2 token it keeps server-side,
// and answers with an HttpOnly session cookie.
export async function login(dhis2Url: string, username: string, password: string): Promise<void> {
    try {
        const { data } = await api.post('/auth/login', { dhis2_url: dhis2Url, username, password })
        useAuthStore().setUser(data.user)
    } catch (e: any) {
        throw new Error(LOGIN_ERRORS[e?.response?.status] ?? 'Login failed')
    }
}

export async function logout(): Promise<void> {
    try {
        await api.post('/auth/logout')
    } catch (e: any) {
        console.warn('Logout request failed; the session expires on its own:', e?.message)
    }
    useAuthStore().clear()
    window.location.href = '/login'
}
