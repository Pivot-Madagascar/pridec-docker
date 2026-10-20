import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

// Create axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8111',
  // Sends the HttpOnly session cookie set by etlhub on /auth/login.
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response) {
      // A 401 on /auth/login is a wrong password, not an expired session.
      if (error.response.status === 401 && error.config?.url !== '/auth/login') {
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

// confirm=true only when the user approved the impact of a 409 confirmation_required (rule R5).
export const withConfirm = (confirm: boolean) => (confirm ? { params: { confirm: true } } : undefined)

export function errorMessage(err: unknown, fallback: string): string {
  const data = (err as { response?: { data?: { message?: unknown; detail?: unknown } } })?.response?.data
  // etlhub answers {message} for its 409/500/501 and {detail} for FastAPI's 404/422.
  if (typeof data?.message === 'string') return data.message
  return typeof data?.detail === 'string' ? data.detail : fallback
}

export interface RequestLog {
  request_id: string
  timestamp: string | null  // UTC ISO 8601, null on old entries
  method: string
  url: string
  status_code: number
  duration_ms: number
  client_host: string | null
  // Job started or read by this request (from its JSON response), if any.
  job_id: string | null
  // Set when the request raised an unhandled exception (status 500).
  error: string | null
  // Why the pipeline gate refused it (409); code 'confirmation_required' when it asked for confirm=true.
  reason?: string | null
  code?: string | null
}

export interface JobLogs {
  job_id: string
  status: string | null   // null once the job record expired (24 h)
  message: string | null
  logs: string | null     // null while a job has not logged anything yet
}

export const trackingApi = {
  listRequests(limit = 50, endpoint?: string) {
    const params: Record<string, any> = { limit }
    if (endpoint) params.endpoint = endpoint
    return api.get('api/tracking/requests', { params })
  },
  getRequest(requestId: string) {
    return api.get(`api/tracking/requests/${encodeURIComponent(requestId)}`)
  },
  getJobLogs(jobId: string) {
    return api.get<JobLogs>(`api/tracking/etl-logs/${encodeURIComponent(jobId)}`)
  }
}

export default api