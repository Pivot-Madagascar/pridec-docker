<template>
  <div class="space-y-6">
    <div class="flex-row-center-between">
      <h1 class="heading-primary">Job Status</h1>
      <button
        @click="checkStatus"
        :disabled="isChecking"
        class="btn-status"
      >
        <svg v-if="isChecking" class="spinner-xs" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        Refresh
      </button>
    </div>

    <div v-if="!jobId" class="card-empty">
      <svg xmlns="http://www.w3.org/2000/svg" class="icon-xl text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
      </svg>
      <h3 class="heading-tertiary text-gray-700 dark:text-gray-300">No Job Selected</h3>
      <p class="text-body text-gray-500 dark:text-gray-400">Start a forecast to see job status here.</p>
      <router-link
        to="/forecast"
        class="btn-fill-yellow"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="icon-sm mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        Run Forecast
      </router-link>
    </div>

    <div v-else class="card card-padded">
      <div class="flex-row-center-between mb-6">
        <div>
          <p class="text-sm text-gray-500 dark:text-gray-400">Job ID</p>
          <p class="text-lg font-mono font-semibold text-gray-900 dark:text-white">{{ jobId }}</p>
        </div>
        <div class="flex-row-center space-x-2">
          <div class="w-3 h-3 rounded-full" :class="statusColor"></div>
          <span class="text-sm font-medium" :class="statusTextColor">{{ status || 'Checking...' }}</span>
        </div>
      </div>

      <div class="space-y-4">
        <div v-if="jobData" class="grid-cols-2-md gap-4">
          <div class="card-info">
            <p class="text-sm text-gray-500 dark:text-gray-400">Started</p>
            <p class="text-sm font-medium text-gray-900 dark:text-white">{{ formatDate(jobData.started) }}</p>
          </div>
          <div class="card-info">
            <p class="text-sm text-gray-500 dark:text-gray-400">Completed</p>
            <p class="text-sm font-medium text-gray-900 dark:text-white">{{ formatDate(jobData.completed) }}</p>
          </div>
        </div>

        <div v-if="jobData?.message" class="alert-success">
          <p class="text-sm text-blue-800 dark:text-blue-300">{{ jobData.message }}</p>
        </div>
      </div>

      <!-- Logs -->
      <div v-if="jobData?.logs" class="mt-6">
        <h3 class="heading-tertiary text-gray-900 dark:text-white mb-3">Logs</h3>
        <div class="log-container">
          <pre class="text-sm text-green-400 font-mono whitespace-pre-wrap">{{ jobData.logs }}</pre>
        </div>
      </div>

      <transition name="fade">
        <div v-if="error" class="alert-error">
          {{ error }}
        </div>
      </transition>
    </div>
  </div>
</template>

<style scoped>
.heading-tertiary {
  @apply text-lg font-semibold mb-2;
}

.text-body {
  @apply mb-6;
  font-size: 0.875rem;
}

.btn-fill-yellow {
  @apply inline-flex items-center px-6 py-3 bg-yellow-400 hover:bg-yellow-500 text-[#131921] font-semibold rounded-lg transition-colors;
}

.card-info {
  @apply p-4 bg-gray-50 dark:bg-gray-800 rounded-lg;
}

.alert-success {
  @apply p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg;
}

.alert-error {
  @apply mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-800 dark:text-red-300;
}

.log-container {
  @apply bg-[#1a1a1a] rounded-lg p-4 max-h-96 overflow-y-auto border border-gray-800;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/services/api'

const route = useRoute()
const jobId = ref(route.params.jobId as string || '')

const isChecking = ref(false)
const status = ref('')
const jobData = ref<any>(null)
const error = ref('')

let pollInterval: number | null = null

const statusColor = computed(() => {
  const s = status.value.toLowerCase()
  if (s === 'completed' || s === 'success') return 'bg-green-500'
  if (s === 'failed' || s === 'error') return 'bg-red-500'
  if (s === 'running') return 'bg-yellow-500'
  return 'bg-gray-400'
})

const statusTextColor = computed(() => {
  const s = status.value.toLowerCase()
  if (s === 'completed' || s === 'success') return 'text-green-600 dark:text-green-400'
  if (s === 'failed' || s === 'error') return 'text-red-600 dark:text-red-400'
  if (s === 'running') return 'text-yellow-600 dark:text-yellow-400'
  return 'text-gray-500 dark:text-gray-400'
})

const checkStatus = async () => {
  if (!jobId.value) return

  isChecking.value = true
  error.value = ''

  try {
    const response = await api.get(`/forecast/status/${jobId.value}`)
    jobData.value = response.data
    status.value = response.data.status || 'unknown'
  } catch (err) {
    console.error('Status check error:', err)
    error.value = 'Failed to fetch job status'
  } finally {
    isChecking.value = false
  }
}

const formatDate = (dateStr: string | null) => {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleString()
}

const pollStatus = () => {
  checkStatus()
  if (status.value === 'running' || status.value === 'pending') {
    pollInterval = window.setInterval(() => {
      checkStatus()
      if (status.value === 'completed' || status.value === 'failed' || status.value === 'success') {
        if (pollInterval) clearInterval(pollInterval)
      }
    }, 3000)
  }
}

onMounted(() => {
  pollStatus()
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>