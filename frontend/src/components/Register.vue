<template>
  <div class="min-h-screen bg-gray-900 flex items-center justify-center p-4">
    <div class="max-w-md w-full space-y-8">
      <div class="text-center">
        <div class="flex items-center justify-center space-x-2 mb-6">
          <Database class="w-12 h-12 text-orange-400" />
          <h1 class="text-3xl font-bold text-white">ETL Dashboard</h1>
        </div>
        <h2 class="text-xl text-gray-300">Create your account</h2>
      </div>
      
      <form class="space-y-6" @submit.prevent="handleRegister">
        <!-- Username -->
        <div>
          <label for="username" class="block text-sm font-medium text-gray-300 mb-1">Username</label>
          <input
            id="username"
            v-model="username"
            type="text"
            autocomplete="username"
            required
            class="w-full px-3 py-3 border border-gray-600 bg-gray-800 text-white rounded-md placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-400 focus:border-transparent"
            placeholder="Enter your username"
          />
        </div>

        <!-- Email -->
        <div>
          <label for="email" class="block text-sm font-medium text-gray-300 mb-1">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            autocomplete="email"
            required
            class="w-full px-3 py-3 border border-gray-600 bg-gray-800 text-white rounded-md placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-400 focus:border-transparent"
            placeholder="Enter your email"
          />
        </div>

        <!-- Password -->
        <div>
          <label for="password" class="block text-sm font-medium text-gray-300 mb-1">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            autocomplete="new-password"
            minlength="6"
            required
            class="w-full px-3 py-3 border border-gray-600 bg-gray-800 text-white rounded-md placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-400 focus:border-transparent"
            placeholder="Enter your password"
          />
        </div>

        <!-- Confirm Password -->
        <div>
          <label for="confirmPassword" class="block text-sm font-medium text-gray-300 mb-1">Confirm Password</label>
          <input
            id="confirmPassword"
            v-model="confirmPassword"
            type="password"
            autocomplete="new-password"
            minlength="6"
            required
            class="w-full px-3 py-3 border border-gray-600 bg-gray-800 text-white rounded-md placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-400 focus:border-transparent"
            placeholder="Confirm your password"
          />
        </div>

        <!-- Submit Button -->
        <div>
          <button
            type="submit"
            :disabled="loading"
            class="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-gray-900 bg-orange-400 hover:bg-orange-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-400 transition-colors disabled:opacity-60"
          >
            {{ loading ? 'Creating Account...' : 'Create Account' }}
          </button>
        </div>

        <!-- Messages -->
        <div v-if="error" class="bg-red-900/30 border border-red-700/50 rounded-lg p-4">
          <div class="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-red-200">{{ error }}</p>
          </div>
        </div>
        
        <div v-if="success" class="bg-green-900/30 border border-green-700/50 rounded-lg p-4">
          <div class="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-green-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-green-200">{{ success }}</p>
          </div>
        </div>

        <!-- Login link -->
        <div class="text-center">
          <span class="text-gray-400">Already have an account? </span>
          <router-link to="/login" class="text-orange-400 hover:text-orange-300">
            Sign in
          </router-link>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Database } from 'lucide-vue-next'
import axios from 'axios'

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const success = ref('')
const loading = ref(false)
const router = useRouter()

const handleRegister = async () => {
  error.value = ''
  success.value = ''
  
  if (password.value !== confirmPassword.value) {
    error.value = "Passwords do not match"
    return
  }
  
  loading.value = true
  
  try {
    await axios.post("/api/auth/register", {
      username: username.value,
      password: password.value,
      email: email.value,
    })
    
    success.value = "Account created successfully. Redirecting to login..."
    
    setTimeout(() => router.push("/login"), 1200)
  } catch (err) {
    if (err.response && err.response.data && err.response.data.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = "Registration failed"
    }
  } finally {
    loading.value = false
  }
}
</script>