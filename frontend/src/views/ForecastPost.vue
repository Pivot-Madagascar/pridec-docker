<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-3xl font-bold text-white">Post Forecast</h1>
    </div>
    
    <div class="bg-gray-800 rounded-lg border border-gray-700 p-6">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 bg-gradient-to-br from-purple-600 via-pink-600 to-indigo-700 rounded-lg flex items-center justify-center text-white font-bold text-lg">
          PF
        </div>
        <h2 class="text-xl font-semibold text-white">Submit Forecast Data</h2>
      </div>

      <!-- Forecast textarea -->
      <div class="mb-4">
        <label for="forecast-data" class="block text-sm font-medium text-gray-300 mb-2">Forecast JSON Data</label>
        <textarea
          id="forecast-data"
          v-model="forecast"
          placeholder='Enter forecast JSON (e.g., {"key": "value"})'
          class="w-full h-48 px-4 py-3 border border-gray-600 bg-gray-900 text-white rounded-lg placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
        ></textarea>
      </div>

      <!-- Dry Run Checkbox -->
      <div class="mb-6">
        <label class="inline-flex items-center text-gray-300">
          <input 
            type="checkbox" 
            v-model="dryRun" 
            class="rounded border-gray-600 bg-gray-700 text-purple-500 focus:ring-2 focus:ring-purple-500 focus:ring-offset-gray-800"
          >
          <span class="ml-2">Dry Run (Test without saving)</span>
        </label>
      </div>

      <!-- Submit Button -->
      <button
        @click="submit"
        :disabled="loading || !canSubmitForecast"
        class="w-full px-4 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-medium rounded-lg transition-all duration-300 flex items-center justify-center space-x-2 disabled:opacity-60 disabled:cursor-not-allowed"
        :title="!canSubmitForecast ? 'Forecast output must be available before posting' : ''"
      >
        <span v-if="loading" class="flex items-center">
          <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Processing...
        </span>
        <span v-else class="flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Submit Forecast
        </span>
      </button>

      <!-- Status Messages -->
      <transition name="fade">
        <div v-if="successMessage" class="mt-6 bg-green-900/30 border border-green-700/50 rounded-lg p-4">
          <div class="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-green-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-green-200">{{ successMessage }}</p>
          </div>
          <p class="text-green-300 text-sm mt-1">Forecast submitted successfully at {{ completionTime }}</p>
        </div>
      </transition>
      
      <transition name="fade">
        <div v-if="error" class="mt-6 bg-red-900/30 border border-red-700/50 rounded-lg p-4">
          <div class="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-red-200">{{ error }}</p>
          </div>
          <p class="text-red-300 text-sm mt-1">Please check your JSON format and try again</p>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useForecastStore } from '@/stores/forecast'
import axios from 'axios'

const forecastStore = useForecastStore()

const forecast = ref('{}')
const dryRun = ref(true)
const loading = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)
const completionTime = ref<string | null>(null)

const canSubmitForecast = computed(() => {
  return forecastStore.hasOutput
})

const submit = async () => {
  if (!canSubmitForecast.value) {
    error.value = 'Forecast output must be available before posting'
    return
  }

  loading.value = true
  error.value = null
  successMessage.value = null

  try {
    // Validate JSON
    JSON.parse(forecast.value)

    const payload = {
      forecast_data: JSON.parse(forecast.value),
      dry_run: dryRun.value
    }

    const token = localStorage.getItem('token')
    if (!token) {
      throw new Error('No authentication token found. Please log in again.')
    }

    await axios.post('/api/post/forecast', payload, {
      headers: { Authorization: `Bearer ${token}` }
    })

    successMessage.value = dryRun.value
      ? 'Dry run completed successfully!'
      : 'Forecast submitted successfully!'
    completionTime.value = new Date().toLocaleTimeString()

  } catch (e: unknown) {
    console.error('Error submitting forecast:', e)
    if (e instanceof Error && e.message.includes('JSON')) {
      error.value = 'Invalid JSON format. Please check your input.'
    } else if (axios.isAxiosError(e)) {
      error.value = e.response?.data?.message || e.message || 'Failed to submit forecast'
    } else if (e instanceof Error) {
      error.value = e.message || 'Failed to submit forecast'
    } else {
      error.value = 'Failed to submit forecast'
    }
  } finally {
    loading.value = false

    // Clear messages after 5 seconds
    setTimeout(() => {
      successMessage.value = null
      error.value = null
    }, 5000)
  }
}

onMounted(async () => {
  await forecastStore.checkOutputStatus()
})
</script>

<style scoped>
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.5s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

textarea {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
}
</style>