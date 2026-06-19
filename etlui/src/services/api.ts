import axios from 'axios'

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
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
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
    // Handle common error cases
    if (error.response) {
      // Server responded with error status
      if (error.response.status === 401) {
        // Unauthorized - redirect to login or clear token
        localStorage.removeItem('token')
        // Optionally redirect to login page
        // router.push('/login')
      }
      // Other error handling can go here
    } else if (error.request) {
      // Request made but no response received
      console.error('Network error:', error.message)
    } else {
      // Error setting up request
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