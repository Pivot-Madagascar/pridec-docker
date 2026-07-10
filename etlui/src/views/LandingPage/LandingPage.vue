<template>
  <div class="space-y-0">
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

    <RecentActivity :activityLog="activityLog" />

    <ForecastModal 
      v-model="showForecastModal"
      @job-created="handleForecastJobCreated"
    />

    <ForecastReportModal 
      v-model="showReportModal"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import api from '@/services/api'

import Notifications from './components/Notifications.vue'
import RecentActivity from './components/RecentActivity.vue'
import StepperCarousel from './components/StepperCarousel.vue'
import ForecastModal from './components/ForecastModal.vue'
import ForecastReportModal from './components/ForecastReportModal.vue'
import { ICONS } from '@/components/Icons'

const showForecastModal = ref(false)
const showReportModal = ref(false)

interface ActivityEntry {
  id: number
  action: string
  message: string
  time: string
  success: boolean
  jobId?: string
}

const lastJobId = ref('')
const forecastReportExists = ref(false)

const notification = ref('')
const notificationType = ref<'success' | 'error'>('success')
const notificationTimer = ref<number | null>(null)
const activityLog = ref<ActivityEntry[]>([])

const commonIcon = ICONS

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
const refreshingReport = ref(false)

const climateSuccess = ref(false)
const diseaseSuccess = ref(false)
const geojsonSuccess = ref(false)

const checkForecastReportExists = async () => {
  refreshingReport.value = true
  try {
    const response = await api.get('/output/forecast_report.html/exists')
    forecastReportExists.value = response.data.exists
    showNotification('Report status refreshed', 'success')
  } catch {
    forecastReportExists.value = false
  } finally {
    refreshingReport.value = false
  }
}

const resetReports = async () => {
  if (!confirm('Are you sure you want to delete the output folder and all its contents?')) return
  try {
    await api.delete('/output/reset')
    forecastReportExists.value = false
    showNotification('Output folder cleared', 'success')
    addActivity('Reset Output', 'Output folder deleted', true)
  } catch (err) {
    showNotification('Failed to reset output', 'error')
    addActivity('Reset Output', 'Failed to delete output folder', false)
  }
}

onMounted(() => {
  checkForecastReportExists()
})

const pipelineSteps = computed(() => [
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
        key: 'view_forecast_report',
        label: 'View Report',
        icon: commonIcon.eye,
        iconClass: 'icon-blue',
        inactive: !forecastReportExists.value,
        statusText: forecastReportExists.value ? 'View forecast report' : 'Report unavailable',
        statusClass: forecastReportExists.value ? 'status-pending' : 'status-pending'
      }
    ],
    onRefresh: checkForecastReportExists,
    onReset: resetReports
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
])

const showNotification = (msg: string, type: 'success' | 'error') => {
  notification.value = msg
  notificationType.value = type
  if (notificationTimer.value) clearTimeout(notificationTimer.value)
  notificationTimer.value = window.setTimeout(() => {
    notification.value = ''
  }, 5000)
}

const addActivity = (action: string, message: string, success: boolean, jobId?: string) => {
  activityLog.value.unshift({
    id: Date.now() + Math.random(),
    action,
    message,
    time: new Date().toLocaleTimeString(),
    success,
    jobId
  })
  if (activityLog.value.length > 20) {
    activityLog.value = activityLog.value.slice(0, 20)
  }
}

const handleActionClick = async (key: string) => {
  if (key === 'navigate_to_forecast') {
    showForecastModal.value = true
    return
  }

  if (key === 'view_forecast_report') {
    showReportModal.value = true
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

  if (key === 'validate_inputs') {
    await validateInputs()
    return
  }

  await triggerETL(key)
}

const handleForecastJobCreated = (jobId: string) => {
  if (jobId) {
    lastJobId.value = jobId
    addActivity('Run Forecast', 'Forecast job started', true, jobId)
  }
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
    addActivity('Fetch Climate', 'Weather data retrieved', true, jobId)
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
    addActivity('Fetch Disease', 'Health data retrieved', true, jobId)
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
    addActivity('Fetch GeoJSON', 'Geospatial boundaries retrieved', true, jobId)
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
      true,
      jobId
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
    addActivity('Validate Inputs', response.data.message || 'Validation passed', true, jobId)
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
</style>