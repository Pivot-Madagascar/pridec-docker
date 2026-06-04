import axios from 'axios'

// Create axios instance
const api = axios.create({
  baseURL: 'http://localhost:8000',
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

export default api