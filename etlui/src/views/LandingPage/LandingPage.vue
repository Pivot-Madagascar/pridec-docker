<template>
  <div class="space-y-8">
    <!-- <HeroSection /> -->

    <section class="dashboard-section">
      <h2 class="section-header">ETL Pipeline</h2>
      <p class="section-subtitle">Follow the workflow step by step</p>

      <StepperCarousel :steps="pipelineSteps" :initial-step="0" @action-click="handleActionClick" />
    </section>

    <Notifications 
      :notification="notification"
      :notificationType="notificationType"
    />

    <section v-if="lastJobId" class="dashboard-section">
      <div class="flex-row-center-between mb-4">
        <h2 class="section-header">Live Logs</h2>
        <div class="flex-row-center space-x-2">
          <span class="text-xs text-gray-500">Job: {{ lastJobId }}</span>
          <span
            class="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold"
            :class="statusBadgeClass"
          >
            <span class="w-2 h-2 rounded-full mr-2" :class="statusDotClass"></span>
            {{ wsStatus || 'Idle' }}
          </span>
          <button
            v-if="lineCount > 0"
            class="text-xs text-gray-400 hover:text-gray-300"
            @click="clearLogs"
          >
            Clear
          </button>
        </div>
      </div>
      <div v-if="statusMessage" class="mt-4 p-3 rounded-lg bg-blue-900/20 border border-blue-800">
        <p class="text-sm text-blue-300">{{ statusMessage }}</p>
      </div>
      <div
        ref="logContainer"
        class="log-container"
      >
        <template v-if="history && !wsLogs.length && !connected">
          <pre class="text-sm text-gray-300 font-mono whitespace-pre-wrap">{{ history }}</pre>
        </template>
        <template v-else-if="combinedLogs">
          <pre class="text-sm text-green-400 font-mono whitespace-pre-wrap">{{ combinedLogs }}</pre>
        </template>
        <template v-else>
          <p class="text-sm text-gray-500 text-center py-8">
            Waiting for logs...
          </p>
        </template>
      </div>
    </section>

    <RecentActivity :activityLog="activityLog" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'
import { useWebSocketLogger } from '@/composables/useWebSocketLogger'

import HeroSection from './components/HeroSection.vue'
import Notifications from './components/Notifications.vue'
import RecentActivity from './components/RecentActivity.vue'
import StepperCarousel from './components/StepperCarousel.vue'

const router = useRouter()

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8111'

const {
  logs: wsLogs,
  history,
  status: wsStatus,
  statusMessage,
  connected,
  connectionError,
  connect,
  disconnect,
  clearLogs: clearWsLogs,
  isRunning,
  isCompleted,
  combinedLogs,
} = useWebSocketLogger({ baseUrl: apiBaseUrl })

const lastJobId = ref('')
const logContainer = ref<HTMLElement | null>(null)
const lineCount = ref(0)

const statusDotClass = computed(() => {
  if (isRunning.value) return 'bg-yellow-500'
  if (wsStatus.value === 'success') return 'bg-green-500'
  if (wsStatus.value === 'error') return 'bg-red-500'
  return 'bg-gray-400'
})

const statusBadgeClass = computed(() => {
  if (isRunning.value) return 'status-badge-running'
  if (wsStatus.value === 'success') return 'status-badge-success'
  if (wsStatus.value === 'error') return 'status-badge-error'
  return 'status-badge-unknown'
})

watch(combinedLogs, (val) => {
  if (!val) {
    lineCount.value = 0
    return
  }
  lineCount.value = val.split('\n').filter(l => l.trim()).length
  nextTick(() => scrollToBottom())
})

watch(lastJobId, (jobId) => {
  if (jobId) {
    connect(jobId)
  }
})

function scrollToBottom() {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

function clearLogs() {
  clearWsLogs()
  lineCount.value = 0
}

interface ActivityEntry {
  id: number
  action: string
  message: string
  time: string
  success: boolean
}

const notification = ref('')
const notificationType = ref<'success' | 'error'>('success')
const notificationTimer = ref<number | null>(null)
const activityLog = ref<ActivityEntry[]>([])

const loading = reactive({
  import_gee: false,
  import_pivot_com: false,
  import_pivot_csb: false,
  build_analytics: false,
  calc_csb_alerts: false,
  update_key: false,
  post_forecast: false,
  validate_inputs: false
})

const results = reactive({
  import_gee: false,
  import_pivot_com: false,
  import_pivot_csb: false,
  build_analytics: false,
  calc_csb_alerts: false,
  update_key: false,
  post_forecast: false,
  validate_inputs: false
})

const loadingClimate = ref(false)
const loadingDisease = ref(false)
const loadingGeoJSON = ref(false)

const climateSuccess = ref(false)
const diseaseSuccess = ref(false)
const geojsonSuccess = ref(false)

const commonIcon = {
  download: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12',
  users: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z',
  clipboardList: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01',
  refresh: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
  cloud: 'M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z',
  beaker: 'M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z',
  map: 'M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7',
  checkCircle: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  lightning: 'M13 10V3L4 14h7v7l9-11h-7z',
  bell: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.595 1.436L4 17h5m6 0v1a3 3 0 01-6 0v-1m6 0H9',
  upload: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12',
  chartBar: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  key: 'M15 7a2 2 0 012 2m4 0a4 4 0 01-4 4 4 4 0 01-4-4V7m4 4v4m-4-4a4 4 0 00-4 4',
  chartPie: 'M11 3.055A9.001 9.001 0 0020.945 13H11V3.055z M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z',
  thumbsUp: 'M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5'
}

const pipelineSteps = [
  {
    id: 'step-1',
    title: 'Data Import',
    actions: [
      {
        key: 'import_gee',
        label: 'Import GEE',
        icon: commonIcon.download,
        iconClass: 'icon-blue',
        loading: loading.import_gee,
        success: results.import_gee,
        statusText: 'Waiting',
        statusClass: 'status-pending',
        loadingText: 'Processing...',
        successText: '✓ Done'
      },
      {
        key: 'import_pivot_com',
        label: 'Import Pivot COM',
        icon: commonIcon.users,
        iconClass: 'icon-green',
        loading: loading.import_pivot_com,
        success: results.import_pivot_com,
        statusText: 'Waiting',
        statusClass: 'status-pending',
        loadingText: 'Processing...',
        successText: '✓ Done'
      },
      {
        key: 'import_pivot_csb',
        label: 'Import Pivot CSB',
        icon: commonIcon.clipboardList,
        iconClass: 'icon-purple',
        loading: loading.import_pivot_csb,
        success: results.import_pivot_csb,
        statusText: 'Waiting',
        statusClass: 'status-pending',
        loadingText: 'Processing...',
        successText: '✓ Done'
      },
      {
        key: 'build_analytics',
        label: 'Build Analytics',
        icon: commonIcon.chartPie,
        iconClass: 'icon-emerald',
        loading: loading.build_analytics,
        success: results.build_analytics,
        statusText: 'Analytics tables',
        statusClass: 'status-pending',
        loadingText: 'Computing...',
        successText: '✓ Ready'
      }
    ]
  },
  {
    id: 'step-2',
    title: 'Data Retrieval',
    actions: [
      {
        key: 'fetch_climate',
        label: 'Fetch Climate',
        icon: commonIcon.cloud,
        iconClass: 'icon-sky',
        loading: loadingClimate.value,
        success: climateSuccess.value,
        statusText: 'Weather & climate',
        statusClass: 'status-pending',
        loadingText: 'Loading...',
        successText: '✓ Success'
      },
      {
        key: 'fetch_disease',
        label: 'Fetch Disease',
        icon: commonIcon.beaker,
        iconClass: 'icon-teal',
        loading: loadingDisease.value,
        success: diseaseSuccess.value,
        statusText: 'Health data',
        statusClass: 'status-pending',
        loadingText: 'Loading...',
        successText: '✓ Success'
      },
      {
        key: 'fetch_geojson',
        label: 'Fetch GeoJSON',
        icon: commonIcon.map,
        iconClass: 'icon-indigo',
        loading: loadingGeoJSON.value,
        success: geojsonSuccess.value,
        statusText: 'Geospatial boundaries',
        statusClass: 'status-pending',
        loadingText: 'Loading...',
        successText: '✓ Success'
      },
      {
        key: 'validate_inputs',
        label: 'Validate Inputs',
        icon: commonIcon.checkCircle,
        iconClass: 'icon-teal',
        loading: loading.validate_inputs,
        success: results.validate_inputs,
        statusText: 'Ready',
        statusClass: 'status-pending',
        loadingText: 'Processing...',
        successText: '✓ Validated'
      }
    ]
  },
  {
    id: 'step-3',
    title: 'Forecast',
    actions: [
      {
        key: 'navigate_to_forecast',
        label: 'Run Forecast',
        subtitle: 'ML forecasting pipeline',
        icon: commonIcon.lightning,
        iconClass: 'icon-orange'
      }
    ]
  },
  {
    id: 'step-4',
    title: 'Approve Forecast',
    actions: [
      {
        key: 'approve_forecast',
        label: 'Approve Forecast',
        icon: commonIcon.thumbsUp,
        iconClass: 'icon-emerald',
        inactive: true,
        statusText: 'Coming soon',
        statusClass: 'status-pending'
      }
    ]
  },
  {
    id: 'step-5',
    title: 'Finalization',
    actions: [
      {
        key: 'post_forecast',
        label: 'Post Forecast',
        icon: commonIcon.upload,
        iconClass: 'icon-rose',
        loading: loading.post_forecast,
        success: results.post_forecast,
        statusText: 'Submit results',
        statusClass: 'status-pending',
        loadingText: 'Publishing...',
        successText: '✓ Published'
      },
      {
        key: 'build_analytics',
        label: 'Build Analytics',
        icon: commonIcon.chartPie,
        iconClass: 'icon-emerald',
        loading: loading.build_analytics,
        success: results.build_analytics,
        statusText: 'Analytics tables',
        statusClass: 'status-pending',
        loadingText: 'Computing...',
        successText: '✓ Ready'
      },
      {
        key: 'calc_csb_alerts',
        label: 'CSB Alerts',
        icon: commonIcon.bell,
        iconClass: 'icon-amber',
        loading: loading.calc_csb_alerts,
        success: results.calc_csb_alerts,
        statusText: 'Alert thresholds',
        statusClass: 'status-pending',
        loadingText: 'Processing...',
        successText: '✓ Done'
      },
      {
        key: 'update_key',
        label: 'Update Key',
        icon: commonIcon.key,
        iconClass: 'icon-slate',
        loading: loading.update_key,
        success: results.update_key,
        statusText: 'API keys',
        statusClass: 'status-pending',
        loadingText: 'Updating...',
        successText: '✓ Updated'
      }
    ]
  }
]

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

const handleActionClick = async (key: string) => {
  if (key === 'navigate_to_forecast') {
    router.push('/forecast')
    return
  }

  if (key.startsWith('fetch_')) {
    switch (key) {
      case 'fetch_climate':
        await fetchClimate()
        break
      case 'fetch_disease':
        await fetchDisease()
        break
      case 'fetch_geojson':
        await fetchGeoJSON()
        break
    }
    return
  }

  await triggerETL(key)
}

const fetchClimate = async () => {
  loadingClimate.value = true
  climateSuccess.value = false
  try {
    const response = await api.post('/fetch_climate')
    const jobId = response.data?.job_id || ''
    if (jobId) lastJobId.value = jobId
    showNotification('Climate data retrieved', 'success')
    climateSuccess.value = true
    addActivity('Fetch Climate', 'Weather data retrieved', true)
  } catch (err) {
    showNotification('Retrieval error', 'error')
    addActivity('Fetch Climate', 'Retrieval failed', false)
    climateSuccess.value = false
  } finally {
    loadingClimate.value = false
  }
}

const fetchDisease = async () => {
  loadingDisease.value = true
  diseaseSuccess.value = false
  try {
    const response = await api.post('/fetch_disease')
    const jobId = response.data?.job_id || ''
    if (jobId) lastJobId.value = jobId
    showNotification('Disease data retrieved', 'success')
    diseaseSuccess.value = true
    addActivity('Fetch Disease', 'Health data retrieved', true)
  } catch (err) {
    showNotification('Retrieval error', 'error')
    addActivity('Fetch Disease', 'Retrieval failed', false)
    diseaseSuccess.value = false
  } finally {
    loadingDisease.value = false
  }
}

const fetchGeoJSON = async () => {
  loadingGeoJSON.value = true
  geojsonSuccess.value = false
  try {
    const response = await api.post('/fetch_geojson')
    const jobId = response.data?.job_id || ''
    if (jobId) lastJobId.value = jobId
    showNotification('GeoJSON retrieved', 'success')
    geojsonSuccess.value = true
    addActivity('Fetch GeoJSON', 'Geospatial boundaries retrieved', true)
  } catch (err) {
    showNotification('Retrieval error', 'error')
    addActivity('Fetch GeoJSON', 'Retrieval failed', false)
    geojsonSuccess.value = false
  } finally {
    loadingGeoJSON.value = false
  }
}

const triggerETL = async (endpoint: string) => {
  if (endpoint === 'approve_forecast') return

  loading[endpoint as keyof typeof loading] = true
  try {
    const response = await api.post(`/${endpoint}`)
    const jobId = response.data?.job_id || ''
    if (jobId) lastJobId.value = jobId
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

const validateInputs = async () => {
  loading.validate_inputs = true
  results.validate_inputs = false
  try {
    const response = await api.post('/validate_inputs')
    const jobId = response.data?.job_id || ''
    if (jobId) lastJobId.value = jobId
    results.validate_inputs = true
    showNotification(response.data.message || 'Inputs validated', 'success')
    addActivity('Validate Inputs', response.data.message || 'Validation passed', true)
  } catch (err) {
    showNotification('Validation failed', 'error')
    addActivity('Validate Inputs', 'Validation failed', false)
    results.validate_inputs = false
  } finally {
    loading.validate_inputs = false
  }
}
</script>

<style scoped>
@reference "tailwindcss";

/* ===== Layout ===== */
.space-y-8 > * + * {
  margin-top: 2rem;
}

.dashboard-section {
  background: #0f172a;
  border-radius: 1rem;
  padding: 2rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.section-header {
  font-size: 1.5rem;
  font-weight: 700;
  color: #f1f5f9;
  margin-bottom: 0.25rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.section-subtitle {
  color: #94a3b8;
  font-size: 0.875rem;
  margin-bottom: 2rem;
}

.log-container {
  background: #1a1a1a;
  border-radius: 0.75rem;
  padding: 1rem;
  height: 400px;
  overflow-y: auto;
  border: 1px solid #334155;
}

.status-badge-success {
  background: #064e3b;
  color: #6ee7b7;
  border: 1px solid #065f46;
}

.status-badge-running {
  background: #78350f;
  color: #fcd34d;
  border: 1px solid #92400e;
}

.status-badge-error {
  background: #7f1d1d;
  color: #fca5a5;
  border: 1px solid #991b1b;
}

.status-badge-unknown {
  background: #1e293b;
  color: #94a3b8;
  border: 1px solid #334155;
}
</style>