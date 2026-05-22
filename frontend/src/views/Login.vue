<template>
  <div class="min-h-screen bg-gray-900 flex items-center justify-center">
    <div class="max-w-md w-full space-y-8">
      <div class="text-center">
        <div class="flex items-center justify-center space-x-2 mb-6">
          <Database class="w-12 h-12 text-orange-400" />
          <h1 class="text-3xl font-bold text-white">ETL Dashboard</h1>
        </div>
        <h2 class="text-xl text-gray-300">Sign in to your account</h2>
      </div>
      
      <form class="space-y-6" @submit.prevent="handleLogin">
        <div>
          <label for="username" class="sr-only">Username</label>
          <input
            id="username"
            name="username"
            type="text"
            autocomplete="username"
            required
            v-model="username"
            class="w-full px-3 py-3 border border-gray-600 bg-gray-800 text-white rounded-md placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-400 focus:border-transparent"
            placeholder="Username"
          />
        </div>
        <div>
          <label for="password" class="sr-only">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            autocomplete="current-password"
            required
            v-model="password"
            class="w-full px-3 py-3 border border-gray-600 bg-gray-800 text-white rounded-md placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-400 focus:border-transparent"
            placeholder="Password"
          />
        </div>
        
        <div class="flex items-center justify-between">
          <div class="flex items-center">
            <input
              id="remember-me"
              name="remember-me"
              type="checkbox"
              class="h-4 w-4 text-orange-400 focus:ring-orange-400 border-gray-600 bg-gray-800 rounded"
            />
            <label for="remember-me" class="ml-2 block text-sm text-gray-300">
              Remember me
            </label>
          </div>
          
          <div class="text-sm">
            <a href="#" class="text-orange-400 hover:text-orange-300">
              Forgot your password?
            </a>
          </div>
        </div>
        
        <div>
          <button
            type="submit"
            :disabled="loading"
            class="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-gray-900 bg-orange-400 hover:bg-orange-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-400 transition-colors disabled:opacity-60"
          >
            {{ loading ? "Signing in..." : "Sign in" }}
          </button>
        </div>
        
        <!-- Error message -->
        <p v-if="error" class="text-sm text-center text-red-500">
          {{ error }}
        </p>
        
        <div class="text-center">
          <span class="text-gray-400">Don't have an account? </span>
          <router-link to="/register" class="text-orange-400 hover:text-orange-300">
            Sign up
          </router-link>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Database } from 'lucide-vue-next'
import axios from 'axios'

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const router = useRouter()

const isDarkMode = ref(false)

const toggleDarkMode = () => {
  isDarkMode.value = !isDarkMode.value
  document.documentElement.classList.toggle('dark', isDarkMode.value)
}

const handleLogin = async () => {
  error.value = ''
  loading.value = true
  try {
    const response = await axios.post('/api/auth/login', {
      username: username.value,
      password: password.value,
    })
    const token = response.data.access_token
    localStorage.setItem('token', token)
    router.push('/dashboard')
  } catch (err) {
    error.value = 'Invalid credentials'
  } finally {
    loading.value = false
  }
}

// Initialize dark mode based on system preference or saved setting
onMounted(() => {
  const savedDarkMode = localStorage.getItem('darkMode')
  if (savedDarkMode !== null) {
    isDarkMode.value = savedDarkMode === 'true'
  } else {
    isDarkMode.value = window.matchMedia('(prefers-color-scheme: dark)').matches
  }
  document.documentElement.classList.toggle('dark', isDarkMode.value)
})
</script>