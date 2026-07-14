import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

// Create axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8111',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response) {
      if (error.response.status === 401) {
        const authStore = useAuthStore()
        authStore.clear()
        window.location.href = '/login'
      }
    } else if (error.request) {
      console.error('Network error:', error.message)
    } else {
      console.error('Request error:', error.message)
    }
    return Promise.reject(error)
  }
)

export interface RequestLog {
  request_id: string
  method: string
  url: string
  status_code: number
  duration_ms: number
  client_host: string | null
  services: ServiceCallLog[]
  error: string | null
}

export interface ServiceCallLog {
  service: string
  method: string
  url: string
  status_code: number | null
  duration_ms: number | null
  error: string | null
}

export const trackingApi = {
  listRequests(limit = 50) {
    return api.get('api/tracking/requests', { params: { limit } })
  },
  getRequest(requestId: string) {
    return api.get(`api/tracking/requests/${encodeURIComponent(requestId)}`)
  }
}

export default api