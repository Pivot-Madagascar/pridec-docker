import { useAuthStore } from '@/stores/auth'

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8111'


export async function handleTokenSubmit(token: string, dhis2Url?: string): Promise<void> {
    const authStore = useAuthStore()
    const res = await fetch(`${API_URL}/auth/validate-token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, dhis2_url: dhis2Url }),
    })
    if (!res.ok) throw new Error('Token validation failed')
    const data = await res.json()
    authStore.setToken(token)
    authStore.setUser(data.user)
}


export async function logout(): Promise<void> {
    const authStore = useAuthStore()
    authStore.clear()
    window.location.href = '/login'
}


export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
    const authStore = useAuthStore()
    return fetch(`${API_URL}${path}`, {
        ...options,
        headers: {
            ...options.headers,
            Authorization: `Bearer ${authStore.token}`,
        },
    })
}