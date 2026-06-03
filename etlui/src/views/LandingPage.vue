<template>
  <div class="space-y-8">
    <!-- Hero Section -->
    <div class="bg-gradient-to-r from-[#131921] to-[#232F3E] rounded-xl p-8 text-white">
      <h1 class="text-4xl font-bold mb-2">Welcome to ETL Hub</h1>
      <p class="text-gray-300 text-lg max-w-2xl">
        Data ingestion, processing, and forecasting platform for malaria surveillance. 
        Manage your ETL pipelines with ease.
      </p>
    </div>

    <!-- Quick Actions -->
    <section>
      <h2 class="text-2xl font-bold text-[#131921] dark:text-white mb-4">Quick Actions</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button
          @click="navigateTo('/forecast')"
          class="flex items-center p-6 bg-yellow-400 hover:bg-yellow-500 text-[#131921] rounded-lg transition-colors shadow-md"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mr-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <div class="text-left">
            <span class="block text-lg font-bold">Run Forecast</span>
            <span class="text-sm opacity-80">Start ML forecasting pipeline</span>
          </div>
        </button>

        <button
          @click="fetchClimate"
          :disabled="loadingClimate"
          class="flex items-center p-6 bg-[#232F3E] text-white rounded-lg border border-gray-600 hover:bg-gray-700 transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mr-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
          </svg>
          <div class="text-left">
            <span class="block text-lg font-bold">Fetch Climate</span>
            <span class="text-sm text-gray-400" v-if="!loadingClimate">Weather & climate data</span>
            <span class="text-sm text-yellow-400" v-else>Fetching...</span>
          </div>
        </button>

        <button
          @click="fetchDisease"
          :disabled="loadingDisease"
          class="flex items-center p-6 bg-[#232F3E] text-white rounded-lg border border-gray-600 hover:bg-gray-700 transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mr-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
          </svg>
          <div class="text-left">
            <span class="block text-lg font-bold">Fetch Disease</span>
            <span class="text-sm text-gray-400" v-if="!loadingDisease">Health data ingestion</span>
            <span class="text-sm text-yellow-400" v-else>Fetching...</span>
          </div>
        </button>

        <button
          @click="fetchGeoJSON"
          :disabled="loadingGeoJSON"
          class="flex items-center p-6 bg-[#232F3E] text-white rounded-lg border border-gray-600 hover:bg-gray-700 transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mr-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
          <div class="text-left">
            <span class="block text-lg font-bold">Fetch GeoJSON</span>
            <span class="text-sm text-gray-400" v-if="!loadingGeoJSON">Geospatial boundaries</span>
            <span class="text-sm text-yellow-400" v-else>Fetching...</span>
          </div>
        </button>
      </div>
    </section>

    <!-- ETL Pipeline -->
    <section>
      <h2 class="text-2xl font-bold text-[#131921] dark:text-white mb-4">ETL Pipeline</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <button
          @click="triggerETL('import_gee')"
          :disabled="loading.import_gee"
          class="p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md hover:border-yellow-400 transition-all text-left disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-semibold text-gray-700">Import GEE</span>
            <span v-if="loading.import_gee" class="text-xs text-yellow-600 font-medium">Running...</span>
            <span v-else-if="results.import_gee" class="text-xs text-green-600 font-medium">✓ Done</span>
          </div>
          <p class="text-xs text-gray-500">Google Earth Engine data import</p>
        </button>

        <button
          @click="triggerETL('import_pivot_com')"
          :disabled="loading.import_pivot_com"
          class="p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md hover:border-yellow-400 transition-all text-left disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-semibold text-gray-700">Import Pivot COM</span>
            <span v-if="loading.import_pivot_com" class="text-xs text-yellow-600 font-medium">Running...</span>
            <span v-else-if="results.import_pivot_com" class="text-xs text-green-600 font-medium">✓ Done</span>
          </div>
          <p class="text-xs text-gray-500">Community health data</p>
        </button>

        <button
          @click="triggerETL('import_pivot_csb')"
          :disabled="loading.import_pivot_csb"
          class="p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md hover:border-yellow-400 transition-all text-left disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-semibold text-gray-700">Import Pivot CSB</span>
            <span v-if="loading.import_pivot_csb" class="text-xs text-yellow-600 font-medium">Running...</span>
            <span v-else-if="results.import_pivot_csb" class="text-xs text-green-600 font-medium">✓ Done</span>
          </div>
          <p class="text-xs text-gray-500">CSB surveillance data</p>
        </button>

        <button
          @click="triggerETL('build_analytics')"
          :disabled="loading.build_analytics"
          class="p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md hover:border-yellow-400 transition-all text-left disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-semibold text-gray-700">Build Analytics</span>
            <span v-if="loading.build_analytics" class="text-xs text-yellow-600 font-medium">Running...</span>
            <span v-else-if="results.build_analytics" class="text-xs text-green-600 font-medium">✓ Done</span>
          </div>
          <p class="text-xs text-gray-500">Compute analytics tables</p>
        </button>

        <button
          @click="triggerETL('calc_csb_alerts')"
          :disabled="loading.calc_csb_alerts"
          class="p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md hover:border-yellow-400 transition-all text-left disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-semibold text-gray-700">CSB Alerts</span>
            <span v-if="loading.calc_csb_alerts" class="text-xs text-yellow-600 font-medium">Running...</span>
            <span v-else-if="results.calc_csb_alerts" class="text-xs text-green-600 font-medium">✓ Done</span>
          </div>
          <p class="text-xs text-gray-500">Calculate alert thresholds</p>
        </button>

        <button
          @click="triggerETL('update_key')"
          :disabled="loading.update_key"
          class="p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md hover:border-yellow-400 transition-all text-left disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-semibold text-gray-700">Update Key</span>
            <span v-if="loading.update_key" class="text-xs text-yellow-600 font-medium">Running...</span>
            <span v-else-if="results.update_key" class="text-xs text-green-600 font-medium">✓ Done</span>
          </div>
          <p class="text-xs text-gray-500">Refresh API keys</p>
        </button>

        <button
          @click="triggerETL('post_forecast')"
          :disabled="loading.post_forecast"
          class="p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md hover:border-yellow-400 transition-all text-left disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-semibold text-gray-700">Post Forecast</span>
            <span v-if="loading.post_forecast" class="text-xs text-yellow-600 font-medium">Running...</span>
            <span v-else-if="results.post_forecast" class="text-xs text-green-600 font-medium">✓ Done</span>
          </div>
          <p class="text-xs text-gray-500">Submit forecast results</p>
        </button>
      </div>
    </section>

    <!-- Notifications -->
    <transition name="fade">
      <div v-if="notification" class="rounded-lg p-4" :class="notificationType === 'success' ? 'bg-green-50 border border-green-200 text-green-800' : 'bg-red-50 border border-red-200 text-red-800'">
        <div class="flex items-center">
          <svg v-if="notificationType === 'success'" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span class="font-medium">{{ notification }}</span>
        </div>
      </div>
    </transition>

    <!-- Recent Activity Log -->
    <section v-if="activityLog.length > 0">
      <h2 class="text-2xl font-bold text-[#131921] dark:text-white mb-4">Recent Activity</h2>
      <div class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div class="divide-y divide-gray-100 dark:divide-gray-800">
          <div v-for="entry in activityLog" :key="entry.id" class="px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
            <div class="flex items-center space-x-3">
              <div class="w-2 h-2 rounded-full" :class="entry.success ? 'bg-green-500' : 'bg-red-500'"></div>
              <div>
                <p class="text-sm font-medium text-gray-900 dark:text-gray-100">{{ entry.action }}</p>
                <p class="text-xs text-gray-500 dark:text-gray-400">{{ entry.message }}</p>
              </div>
            </div>
            <span class="text-xs text-gray-400 dark:text-gray-500">{{ entry.time }}</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()

interface ActivityEntry {
  id: number
  action: string
  message: string
  time: string
  success: boolean
}

const loading = reactive({
  import_gee: false,
  import_pivot_com: false,
  import_pivot_csb: false,
  build_analytics: false,
  calc_csb_alerts: false,
  update_key: false,
  post_forecast: false
})

const results = reactive({
  import_gee: false,
  import_pivot_com: false,
  import_pivot_csb: false,
  build_analytics: false,
  calc_csb_alerts: false,
  update_key: false,
  post_forecast: false
})

const loadingClimate = ref(false)
const loadingDisease = ref(false)
const loadingGeoJSON = ref(false)

const notification = ref('')
const notificationType = ref<'success' | 'error'>('success')
const notificationTimer = ref<number | null>(null)

const activityLog = ref<ActivityEntry[]>([])

const navigateTo = (path: string) => {
  router.push(path)
}

const showNotification = (msg: string, type: 'success' | 'error') => {
  notification.value = msg
  notificationType.value = type
  if (notificationTimer.value) clearTimeout(notificationTimer.value)
  notificationTimer.value = window.setTimeout(() => {
    notification.value = ''
  }, 5000)
}

const addActivity = (action: string, message: string, success: boolean) => {
  activityLog.value.unshift({
    id: Date.now() + Math.random(),
    action,
    message,
    time: new Date().toLocaleTimeString(),
    success
  })
  if (activityLog.value.length > 20) {
    activityLog.value = activityLog.value.slice(0, 20)
  }
}

const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const fetchClimate = async () => {
  loadingClimate.value = true
  try {
    await axios.post('/fetch_climate', {}, { headers: getAuthHeaders() })
    showNotification('Climate data fetched successfully', 'success')
    addActivity('Fetch Climate', 'Climate data retrieved', true)
  } catch (err) {
    showNotification('Failed to fetch climate data', 'error')
    addActivity('Fetch Climate', 'Failed to retrieve climate data', false)
  } finally {
    loadingClimate.value = false
  }
}

const fetchDisease = async () => {
  loadingDisease.value = true
  try {
    await axios.post('/fetch_disease', {}, { headers: getAuthHeaders() })
    showNotification('Disease data fetched successfully', 'success')
    addActivity('Fetch Disease', 'Disease data retrieved', true)
  } catch (err) {
    showNotification('Failed to fetch disease data', 'error')
    addActivity('Fetch Disease', 'Failed to retrieve disease data', false)
  } finally {
    loadingDisease.value = false
  }
}

const fetchGeoJSON = async () => {
  loadingGeoJSON.value = true
  try {
    await axios.post('/fetch_geojson', {}, { headers: getAuthHeaders() })
    showNotification('GeoJSON data fetched successfully', 'success')
    addActivity('Fetch GeoJSON', 'Geospatial boundaries retrieved', true)
  } catch (err) {
    showNotification('Failed to fetch GeoJSON data', 'error')
    addActivity('Fetch GeoJSON', 'Failed to retrieve GeoJSON', false)
  } finally {
    loadingGeoJSON.value = false
  }
}

const triggerETL = async (endpoint: string) => {
  loading[endpoint as keyof typeof loading] = true
  try {
    const response = await axios.post(`/${endpoint}`, {}, { headers: getAuthHeaders() })
    results[endpoint as keyof typeof results] = true
    showNotification(response.data.message || `${endpoint} completed`, 'success')
    addActivity(
      endpoint.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      response.data.message || 'ETL step completed',
      true
    )
  } catch (err) {
    showNotification(`Failed: ${endpoint}`, 'error')
    addActivity(
      endpoint.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      'ETL step failed',
      false
    )
  } finally {
    loading[endpoint as keyof typeof loading] = false
  }
}
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
