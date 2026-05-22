<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-3xl font-bold text-white">Forecasting</h1>
    </div>

    <div class="bg-gray-800 rounded-lg border border-gray-700 p-6">
      <h2 class="text-xl font-semibold text-white mb-4">ML Forecasting Services</h2>
      <p class="text-gray-400 mb-6">Trigger and manage your forecasting models here.</p>

      <!-- Configuration Section -->
      <div class="mb-6">
        <h3 class="text-lg font-medium text-white mb-3">Forecast Configuration</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="bg-gray-700 rounded p-4">
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-300">Configuration Status</span>
              <div :class="['w-3 h-3 rounded-full', configUploaded ? 'bg-green-500' : 'bg-red-500']"></div>
            </div>
            <p class="text-xs text-gray-400 mt-1">{{ configUploaded ? 'Configuration uploaded' : 'Configuration needed' }}</p>
          </div>
        </div>
      </div>

      <!-- Data Status Section -->
      <div class="mb-6">
        <h3 class="text-lg font-medium text-white mb-3">Data Status</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div class="bg-gray-700 rounded p-4">
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-300">Climate Data</span>
              <div :class="['w-3 h-3 rounded-full', dataStatus.climate ? 'bg-green-500' : 'bg-red-500']"></div>
            </div>
            <p class="text-xs text-gray-400 mt-1">{{ dataStatus.climate ? 'Available' : 'Not Available' }}</p>
          </div>
          <div class="bg-gray-700 rounded p-4">
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-300">Disease Data</span>
              <div :class="['w-3 h-3 rounded-full', dataStatus.disease ? 'bg-green-500' : 'bg-red-500']"></div>
            </div>
            <p class="text-xs text-gray-400 mt-1">{{ dataStatus.disease ? 'Available' : 'Not Available' }}</p>
          </div>
          <div class="bg-gray-700 rounded p-4">
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-300">External Data</span>
              <div :class="['w-3 h-3 rounded-full', dataStatus.external ? 'bg-green-500' : 'bg-red-500']"></div>
            </div>
            <p class="text-xs text-gray-400 mt-1">{{ dataStatus.external ? 'Available' : 'Not Available' }}</p>
          </div>
          <div class="bg-gray-700 rounded p-4">
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-300">Polygon Data</span>
              <div :class="['w-3 h-3 rounded-full', dataStatus.polygon ? 'bg-green-500' : 'bg-red-500']"></div>
            </div>
            <p class="text-xs text-gray-400 mt-1">{{ dataStatus.polygon ? 'Available' : 'Not Available' }}</p>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex flex-wrap gap-4">
        <button
          @click="triggerForecast"
          :disabled="!canTriggerForecast || isForecasting"
          class="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
        >
          {{ isForecasting ? 'Preparing Files...' : 'Prepare Files for Forecast' }}
        </button>

        <button
          @click="runForecastTest"
          :disabled="isRunningForecastTest"
          class="bg-orange-600 hover:bg-orange-700 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
        >
          {{ isRunningForecastTest ? 'Running Forecast...' : 'Run Forecast (with logs)' }}
        </button>

        <router-link
          to="/forecast-post"
          :class="[
            'inline-flex items-center px-4 py-2 rounded-lg transition-colors',
            forecastCompleted ? 'bg-purple-600 hover:bg-purple-700 text-white' : 'bg-gray-600 text-gray-400 cursor-not-allowed pointer-events-none'
          ]"
          :title="!forecastCompleted ? 'Complete forecast first to post results' : 'Post forecast results'"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Post Forecast
        </router-link>

        <button
          @click="checkDataStatus"
          class="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          Refresh Status
        </button>
      </div>

      <!-- Messages -->
      <div v-if="message" class="mt-4 p-4 rounded-lg" :class="messageType === 'success' ? 'bg-green-800 text-green-200' : 'bg-red-800 text-red-200'">
        {{ message }}
      </div>

      <!-- Forecast Results -->
      <div v-if="forecastResult" class="mt-6">
        <h3 class="text-lg font-medium text-white mb-3">Forecast Status</h3>
        <div class="bg-gray-700 rounded p-4">
          <div class="flex items-center space-x-3 mb-3">
            <div :class="['w-4 h-4 rounded-full', forecastCompleted ? 'bg-green-500' : 'bg-blue-500 animate-pulse']"></div>
            <span class="text-white font-medium">
              {{ forecastCompleted ? 'Forecast Completed' : 'Forecast Running...' }}
            </span>
          </div>
          <!-- <pre class="text-sm text-gray-300 whitespace-pre-wrap">{{ forecastResult }}</pre> -->
        </div>
      </div>

      <!-- Forecast Logs -->
      <div v-if="forecastLogs" class="mt-6">
        <h3 class="text-lg font-medium text-white mb-3">Forecast Service Logs</h3>
        <div class="bg-gray-900 rounded p-4 max-h-96 overflow-y-auto">
          <pre class="text-sm text-green-400 whitespace-pre-wrap font-mono">{{ forecastLogs }}</pre>
        </div>
      </div>

      <!-- Docker Forecast Logs -->
      <div v-if="dockerForecastLogs" class="mt-6">
        <h3 class="text-lg font-medium text-white mb-3">Docker Forecast Service Logs</h3>
        <div class="bg-gray-900 rounded p-4 max-h-96 overflow-y-auto">
          <pre class="text-sm text-blue-400 whitespace-pre-wrap font-mono">{{ dockerForecastLogs }}</pre>
        </div>
      </div>

      <!-- Forecast Output Files -->
      <div v-if="forecastCompleted && outputFiles.length > 0" class="mt-6">
        <h3 class="text-lg font-medium text-white mb-3">Forecast Output Files ({{ outputFiles.length }})</h3>
        <div class="space-y-3">
          <div v-for="file in outputFiles" :key="file.filename"
                class="p-4 rounded-lg bg-green-900/20 border border-green-600">
            <div class="flex justify-between items-start">
              <div class="flex-1">
                <div class="flex items-center space-x-3">
                  <div class="w-8 h-8 bg-green-900/30 rounded flex items-center justify-center">
                    <span class="text-xs">📄</span>
                  </div>
                  <div>
                    <p class="text-white font-medium">{{ file.filename }}</p>
                    <p class="text-gray-400 text-sm">{{ formatFileSize(file.file_size_bytes) }}</p>
                  </div>
                </div>
                <div class="mt-2 text-xs text-gray-500">
                  <p>Path: {{ file.file_path }}</p>
                  <p>Last Modified: {{ formatUploadTime(file.last_modified) }}</p>
                </div>
              </div>
              <button
                v-if="file.filename === 'forecast_report.html'"
                @click="viewForecastReport"
                class="text-green-400 hover:text-green-300 transition-colors ml-4"
                title="View forecast report"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- JSON Data Files List -->
      <div v-if="jsonFiles.length > 0" class="mt-6">
        <h3 class="text-lg font-medium text-white mb-3">JSON Data Files ({{ jsonFiles.length }})</h3>
        <div class="space-y-3">
          <div v-for="file in jsonFiles" :key="file.filename"
               class="p-4 rounded-lg bg-gray-700 border border-gray-600">
            <div class="flex justify-between items-start">
              <div class="flex-1">
                <div class="flex items-center space-x-3">
                  <div class="w-8 h-8 bg-blue-900/30 rounded flex items-center justify-center">
                    <span class="text-xs">📄</span>
                  </div>
                  <div>
                    <p class="text-white font-medium">{{ file.filename }}</p>
                    <p class="text-gray-400 text-sm">{{ formatFileSize(file.file_size_bytes) }} • {{ file.data_type.toUpperCase() }} • {{ file.record_count }} records</p>
                  </div>
                </div>
                <div class="mt-2 text-xs text-gray-500">
                  <p>Path: {{ file.file_path }}</p>
                  <p>Last Modified: {{ formatUploadTime(file.last_modified) }}</p>
                </div>
              </div>
              <button
                @click="downloadJsonFile(file.filename)"
                class="text-blue-400 hover:text-blue-300 transition-colors ml-4"
                title="Download file"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Uploaded Files List -->
      <div v-if="uploadedFiles.length > 0" class="mt-6">
        <h3 class="text-lg font-medium text-white mb-3">Uploaded External Data ({{ uploadedFiles.length }})</h3>
        <div class="space-y-3">
          <div v-for="file in uploadedFiles" :key="file.redis_key"
               class="p-4 rounded-lg bg-gray-700 border border-gray-600">
            <div class="flex justify-between items-start">
              <div class="flex-1">
                <div class="flex items-center space-x-3">
                  <div class="w-8 h-8 bg-purple-900/30 rounded flex items-center justify-center">
                    <span class="text-xs">{{ getFileIcon(file.filename) }}</span>
                  </div>
                  <div>
                    <p class="text-white font-medium">{{ file.filename }}</p>
                    <p class="text-gray-400 text-sm">{{ formatFileSize(file.file_size_bytes) }} • {{ file.file_type.toUpperCase() }}</p>
                  </div>
                </div>
                <div class="mt-2 text-xs text-gray-500">
                  <p>Redis Key: {{ file.redis_key }}</p>
                  <p>Uploaded: {{ formatUploadTime(file.upload_timestamp) }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

interface UploadedFile {
  redis_key: string
  filename: string
  file_size_bytes: number
  file_type: string
  upload_timestamp: string
}

interface JsonFile {
  filename: string
  file_path: string
  file_size_bytes: number
  data_type: string
  record_count: number
  last_modified: string
  available: boolean
}

const isForecasting = ref(false)
const isRunningForecastTest = ref(false)
const message = ref('')
const messageType = ref('')
const forecastResult = ref('')
const forecastLogs = ref('')
const dockerForecastLogs = ref('')
const uploadedFiles = ref<UploadedFile[]>([])
const jsonFiles = ref<JsonFile[]>([])
const forecastCompletionPolling = ref<number | null>(null)
const forecastLogsPolling = ref<number | null>(null)
const dockerForecastLogsPolling = ref<number | null>(null)
const forecastCompleted = ref(false)
const configUploaded = ref(false)
const outputFiles = ref<Array<{filename: string, file_path: string, file_size_bytes: number, last_modified: string, available: boolean}>>([])

const dataStatus = ref({
  climate: false,
  disease: false,
  external: false,
  polygon: false
})

const canTriggerForecast = computed(() => {
  return dataStatus.value.climate && dataStatus.value.disease && dataStatus.value.external && dataStatus.value.polygon && configUploaded.value
})

const showMessage = (msg: string, type: 'success' | 'error' = 'success') => {
  message.value = msg
  messageType.value = type
  setTimeout(() => {
    message.value = ''
  }, 5000)
}

const checkDataStatus = async () => {
  try {

    // Check climate data availability from cache
    const climateResponse = await axios.get('/api/fetch/climate-data-cached')
    dataStatus.value.climate = climateResponse.data.success

    // Check disease data availability from cache
    const diseaseResponse = await axios.get('/api/fetch/disease-data-cached')
    dataStatus.value.disease = diseaseResponse.data.success

    // Check external data availability from Redis
    try {
      const externalResponse = await axios.get('/api/raw-file/external_data')
      dataStatus.value.external = externalResponse.data && externalResponse.data.data && externalResponse.data.data.filename
    } catch (error) {
      console.error('Error checking external data status:', error)
      dataStatus.value.external = false
    }

    // Check polygon data availability from Redis
    try {
      const polygonResponse = await axios.get('/api/raw-file/orgunit_polygons')
      dataStatus.value.polygon = polygonResponse.data && polygonResponse.data.data && polygonResponse.data.data.filename
    } catch (error) {
      console.error('Error checking polygon status:', error)
      dataStatus.value.polygon = false
    }

    // Check forecast configuration availability
    try {
      const configResponse = await axios.get('/api/forecast/config')
      configUploaded.value = configResponse.status === 200
    } catch (error) {
      console.error('Error checking config status:', error)
      configUploaded.value = false
    }

  } catch (error) {
    console.error('Error checking data status:', error)
    showMessage('Error checking data status', 'error')
  }
}

const downloadJsonFile = async (filename: string) => {
  try {
    const response = await axios.get(`/api/data/json-files/${filename}`, {
      responseType: 'blob'
    })

    // Create a download link
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)

  } catch (error) {
    console.error('Error downloading JSON file:', error)
    showMessage('Error downloading JSON file', 'error')
  }
}

const triggerForecast = async () => {
  if (!canTriggerForecast.value) {
    showMessage('All required data must be available before running forecast', 'error')
    return
  }

  isForecasting.value = true
  forecastCompleted.value = false
  outputFiles.value = []
  forecastLogs.value = '' // Clear previous logs

  try {
    const token = localStorage.getItem('token')
    const headers = token ? { Authorization: `Bearer ${token}` } : {}

    // Call the API that prepares input files for forecasting
    const response = await axios.post('/api/forecast/prepare-input-files', {}, { headers })

    if (response.data.success) {
      showMessage('Input files prepared successfully! Ready for forecasting.', 'success')
      forecastResult.value = JSON.stringify(response.data.data, null, 2)
      forecastCompleted.value = false // Reset completion status
    } else {
      showMessage(`File preparation failed: ${response.data.message}`, 'error')
    }
  } catch (error) {
    console.error('Error triggering forecast:', error)
    let errorMessage = 'Unknown error'
    if (axios.isAxiosError(error)) {
      errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message
    } else if (error instanceof Error) {
      errorMessage = error.message
    }
    showMessage(`Error starting forecast: ${errorMessage}`, 'error')
  } finally {
    isForecasting.value = false
  }
}

const runForecastTest = async () => {
  isRunningForecastTest.value = true
  forecastResult.value = '' // Clear previous results
  forecastLogs.value = '' // Clear previous logs

  try {
    const token = localStorage.getItem('token')
    if (!token) {
      showMessage('Authentication required. Please log in first.', 'error')
      return
    }

    const headers = { Authorization: `Bearer ${token}` }

    // Call the backend endpoint that proxies to plumber app
    const response = await axios.post('/api/forecast/run-full', {}, { headers })

    if (response.data.success) {
      showMessage('Forecast completed successfully!', 'success')
      forecastResult.value = JSON.stringify(response.data.data, null, 2)
      forecastCompleted.value = true
    } else {
      showMessage(`Forecast failed: ${response.data.message}`, 'error')
      forecastResult.value = JSON.stringify(response.data, null, 2)
    }
  } catch (error) {
    console.error('Error running forecast:', error)
    let errorMessage = 'Unknown error'
    if (axios.isAxiosError(error)) {
      errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message
    } else if (error instanceof Error) {
      errorMessage = error.message
    }
    showMessage(`Error running forecast: ${errorMessage}`, 'error')
    forecastResult.value = `Error: ${errorMessage}`
  } finally {
    isRunningForecastTest.value = false
  }
}

const loadUploadedFiles = async () => {
  try {
    const token = localStorage.getItem('token')
    if (!token) return

    const response = await axios.get('/api/raw-files/list')

    uploadedFiles.value = response.data.data.files || []
  } catch (error) {
    console.error('Error loading uploaded files:', error)
  }
}

const getFileIcon = (filename: string) => {
  const ext = filename.toLowerCase().split('.').pop()
  switch (ext) {
    case 'csv': return '📊'
    case 'xlsx': case 'xls': return '📈'
    case 'json': case 'geojson': return '📄'
    default: return '📄'
  }
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatUploadTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleString()
}

const viewForecastReport = () => {
  // Open the forecast report in a new tab
  window.open('/api/forecast/output/forecast_report.html', '_blank')
}

onMounted(() => {
  checkDataStatus()
  loadUploadedFiles()
})

onUnmounted(() => {
  // Clear all polling intervals
  if (forecastCompletionPolling.value) {
    clearInterval(forecastCompletionPolling.value)
  }
  if (forecastLogsPolling.value) {
    clearInterval(forecastLogsPolling.value)
  }
  if (dockerForecastLogsPolling.value) {
    clearInterval(dockerForecastLogsPolling.value)
  }
})
</script>
