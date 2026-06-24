<template>
  <div class="space-y-8">
    <!-- Hero Section -->
    <HeroSection />

    <!-- ETL Pipeline Stepper -->
    <section class="dashboard-section">
      <h2 class="section-header">ETL Pipeline</h2>
      <p class="section-subtitle">Follow the workflow step by step</p>
      
      <div class="stepper">
        <!-- Step 1: Data Import -->
        <div class="stepper-step">
          <div class="stepper-indicator">
            <svg class="step-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
          </div>
          <div class="stepper-content">
            <h3 class="stepper-title">
              Data Import
              <span class="stepper-badge">Step 1</span>
            </h3>
            <div class="action-grid">
              <button @click="triggerETL('import_gee')" :disabled="loading.import_gee" class="action-card btn-etl" :class="{ 'card-success': results.import_gee }">
                <div class="card-icon icon-blue">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon-svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div class="card-content">
                  <span class="card-title">Import GEE</span>
                  <span class="card-status">
                    <span v-if="loading.import_gee" class="status-running">
                      <span class="spinner"></span>
                      Processing...
                    </span>
                    <span v-else-if="results.import_gee" class="status-done">✓ Done</span>
                    <span v-else class="status-pending">Waiting</span>
                  </span>
                </div>
              </button>

              <button @click="triggerETL('import_pivot_com')" :disabled="loading.import_pivot_com" class="action-card btn-etl" :class="{ 'card-success': results.import_pivot_com }">
                <div class="card-icon icon-green">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon-svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <div class="card-content">
                  <span class="card-title">Import Pivot COM</span>
                  <span class="card-status">
                    <span v-if="loading.import_pivot_com" class="status-running">
                      <span class="spinner"></span>
                      Processing...
                    </span>
                    <span v-else-if="results.import_pivot_com" class="status-done">✓ Done</span>
                    <span v-else class="status-pending">Waiting</span>
                  </span>
                </div>
              </button>

              <button @click="triggerETL('import_pivot_csb')" :disabled="loading.import_pivot_csb" class="action-card btn-etl" :class="{ 'card-success': results.import_pivot_csb }">
                <div class="card-icon icon-purple">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon-svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                  </svg>
                </div>
                <div class="card-content">
                  <span class="card-title">Import Pivot CSB</span>
                  <span class="card-status">
                    <span v-if="loading.import_pivot_csb" class="status-running">
                      <span class="spinner"></span>
                      Processing...
                    </span>
                    <span v-else-if="results.import_pivot_csb" class="status-done">✓ Done</span>
                    <span v-else class="status-pending">Waiting</span>
                  </span>
                </div>
              </button>
            </div>
          </div>
        </div>

        <!-- Step 2: Data Fetch -->
        <div class="stepper-step">
          <div class="stepper-indicator">
            <svg class="step-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>
          <div class="stepper-content">
            <h3 class="stepper-title">
              Data Retrieval
              <span class="stepper-badge">Step 2</span>
            </h3>
            <div class="action-grid">
              <button @click="fetchClimate" :disabled="loadingClimate" class="action-card btn-fetch" :class="{ 'card-success': climateSuccess }">
                <div class="card-icon icon-sky">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon-svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                  </svg>
                </div>
                <div class="card-content">
                  <span class="card-title">Fetch Climate</span>
                  <span class="card-status">
                    <span v-if="loadingClimate" class="status-running">
                      <span class="spinner"></span>
                      Loading...
                    </span>
                    <span v-else-if="climateSuccess" class="status-done">✓ Success</span>
                    <span v-else class="status-pending">Weather & climate</span>
                  </span>
                </div>
              </button>

              <button @click="fetchDisease" :disabled="loadingDisease" class="action-card btn-fetch" :class="{ 'card-success': diseaseSuccess }">
                <div class="card-icon icon-teal">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon-svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                  </svg>
                </div>
                <div class="card-content">
                  <span class="card-title">Fetch Disease</span>
                  <span class="card-status">
                    <span v-if="loadingDisease" class="status-running">
                      <span class="spinner"></span>
                      Loading...
                    </span>
                    <span v-else-if="diseaseSuccess" class="status-done">✓ Success</span>
                    <span v-else class="status-pending">Health data</span>
                  </span>
                </div>
              </button>

              <button @click="fetchGeoJSON" :disabled="loadingGeoJSON" class="action-card btn-fetch" :class="{ 'card-success': geojsonSuccess }">
                <div class="card-icon icon-indigo">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon-svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                  </svg>
                </div>
                <div class="card-content">
                  <span class="card-title">Fetch GeoJSON</span>
                  <span class="card-status">
                    <span v-if="loadingGeoJSON" class="status-running">
                      <span class="spinner"></span>
                      Loading...
                    </span>
                    <span v-else-if="geojsonSuccess" class="status-done">✓ Success</span>
                    <span v-else class="status-pending">Geospatial boundaries</span>
                  </span>
                </div>
              </button>
            </div>
          </div>
        </div>

        <!-- Step 3: Validation -->
        <div class="stepper-step">
          <div class="stepper-indicator">
            <svg class="step-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="stepper-content">
            <h3 class="stepper-title">
              Validation
              <span class="stepper-badge">Step 3</span>
            </h3>
            <div class="action-grid">
              <button @click="validateInputs" :disabled="loading.validate_inputs" class="action-card btn-etl" :class="{ 'card-success': results.validate_inputs }">
                <div class="card-icon icon-teal">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon-svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div class="card-content">
                  <span class="card-title">Validate Inputs</span>
                  <span class="card-status">
                    <span v-if="loading.validate_inputs" class="status-running">
                      <span class="spinner"></span>
                      Processing...
                    </span>
                    <span v-else-if="results.validate_inputs" class="status-done">✓ Validated</span>
                    <span v-else class="status-pending">Ready</span>
                  </span>
                </div>
              </button>
            </div>
          </div>
        </div>

        <!-- Step 4: Forecast -->
        <div class="stepper-step">
          <div class="stepper-indicator">
            <svg class="step-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div class="stepper-content">
            <h3 class="stepper-title">
              Forecast
              <span class="stepper-badge">Step 4</span>
            </h3>
            <div class="action-grid">
              <button @click="navigateTo('/forecast')" class="action-card btn-forecast-primary">
                <div class="card-icon icon-orange">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon-svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <div class="card-content">
                  <span class="card-title">Run Forecast</span>
                  <span class="card-subtitle">ML forecasting pipeline</span>
                </div>
              </button>

              <button @click="triggerETL('calc_csb_alerts')" :disabled="loading.calc_csb_alerts" class="action-card btn-etl" :class="{ 'card-success': results.calc_csb_alerts }">
                <div class="card-icon icon-amber">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon-svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                  </svg>
                </div>
                <div class="card-content">
                  <span class="card-title">CSB Alerts</span>
                  <span class="card-status">
                    <span v-if="loading.calc_csb_alerts" class="status-running">
                      <span class="spinner"></span>
                      Processing...
                    </span>
                    <span v-else-if="results.calc_csb_alerts" class="status-done">✓ Done</span>
                    <span v-else class="status-pending">Alert thresholds</span>
                  </span>
                </div>
              </button>

              <button @click="triggerETL('post_forecast')" :disabled="loading.post_forecast" class="action-card btn-etl" :class="{ 'card-success': results.post_forecast }">
                <div class="card-icon icon-rose">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon-svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <div class="card-content">
                  <span class="card-title">Post Forecast</span>
                  <span class="card-status">
                    <span v-if="loading.post_forecast" class="status-running">
                      <span class="spinner"></span>
                      Publishing...
                    </span>
                    <span v-else-if="results.post_forecast" class="status-done">✓ Published</span>
                    <span v-else class="status-pending">Submit results</span>
                  </span>
                </div>
              </button>
            </div>
          </div>
        </div>

        <!-- Step 4: Analytics -->
        <div class="stepper-step">
          <div class="stepper-indicator">
            <svg class="step-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div class="stepper-content">
            <h3 class="stepper-title">
              Analytics
              <span class="stepper-badge">Step 5</span>
            </h3>
            <div class="action-grid gapless">
              <button @click="triggerETL('build_analytics')" :disabled="loading.build_analytics" class="action-card btn-etl" :class="{ 'card-success': results.build_analytics }">
                <div class="card-icon icon-emerald">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon-svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
                  </svg>
                </div>
                <div class="card-content">
                  <span class="card-title">Build Analytics</span>
                  <span class="card-status">
                    <span v-if="loading.build_analytics" class="status-running">
                      <span class="spinner"></span>
                      Computing...
                    </span>
                    <span v-else-if="results.build_analytics" class="status-done">✓ Ready</span>
                    <span v-else class="status-pending">Analytics tables</span>
                  </span>
                </div>
              </button>

              <button @click="triggerETL('update_key')" :disabled="loading.update_key" class="action-card btn-etl" :class="{ 'card-success': results.update_key }">
                <div class="card-icon icon-slate">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon-svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a4 4 0 01-4 4 4 4 0 01-4-4V7m4 4v4m-4-4a4 4 0 00-4 4" />
                  </svg>
                </div>
                <div class="card-content">
                  <span class="card-title">Update Key</span>
                  <span class="card-status">
                    <span v-if="loading.update_key" class="status-running">
                      <span class="spinner"></span>
                      Updating...
                    </span>
                    <span v-else-if="results.update_key" class="status-done">✓ Updated</span>
                    <span v-else class="status-pending">API keys</span>
                  </span>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Notifications -->
    <Notifications 
      :notification="notification"
      :notificationType="notificationType"
    />

    <!-- Recent Activity Log -->
    <RecentActivity :activityLog="activityLog" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'

import HeroSection from './components/HeroSection.vue'
import Notifications from './components/Notifications.vue'
import RecentActivity from './components/RecentActivity.vue'

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

const fetchClimate = async () => {
  loadingClimate.value = true
  climateSuccess.value = false
  try {
    await api.post('/fetch_climate')
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
    await api.post('/fetch_disease')
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
    await api.post('/fetch_geojson')
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
  loading[endpoint as keyof typeof loading] = true
  try {
    const response = await api.post(`/${endpoint}`)
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

/* ===== Dashboard Layout ===== */
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

/* ===== Stepper ===== */
.stepper {
  position: relative;
  padding-left: 0;
}

.stepper-step {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 2rem;
  position: relative;
}

.stepper-step:last-child {
  margin-bottom: 0;
}

.stepper-step:not(:last-child)::after {
  content: '';
  position: absolute;
  left: 1.35rem;
  top: 2.75rem;
  bottom: -1rem;
  width: 2px;
  background: #475569;
  z-index: 0;
}

/* ===== Step Indicator ===== */
.stepper-indicator {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 50%;
  background: #4f46e5;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
  box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.step-icon {
  width: 1.25rem;
  height: 1.25rem;
}

/* ===== Step Content ===== */
.stepper-content {
  flex: 1;
  min-width: 0;
}

.stepper-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.stepper-badge {
  font-size: 0.75rem;
  font-weight: 500;
  color: #a5b4fc;
  background: rgba(99, 102, 241, 0.15);
  padding: 0.25rem 0.625rem;
  border-radius: 9999px;
  text-transform: uppercase;
  letter-spacing: 0.025em;
  border: 1px solid rgba(99, 102, 241, 0.3);
}

/* ===== Action Grid ===== */
.action-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.action-grid.gapless {
  grid-template-columns: repeat(2, 1fr);
  max-width: 66.666%;
}

/* ===== Action Cards ===== */
.action-card {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.25rem;
  background: #1e293b;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 0.75rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  text-align: left;
  width: 100%;
  position: relative;
  overflow: hidden;
}

.action-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at top left, rgba(99, 102, 241, 0.1), transparent 60%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.action-card:hover:not(:disabled)::before {
  opacity: 1;
}

.action-card:hover:not(:disabled) {
  border-color: rgba(99, 102, 241, 0.5);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2), 0 0 0 1px rgba(99, 102, 241, 0.1);
  transform: translateY(-4px);
}

.action-card:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-card.card-success {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.15);
  box-shadow: 0 0 15px rgba(16, 185, 129, 0.2);
}

/* ===== Cards Icons ===== */
.card-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.625rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
}

.icon-svg {
  width: 1.25rem;
  height: 1.25rem;
  color: white;
}

.icon-blue { background: #6366f1; }
.icon-sky { background: #0ea5e9; }
.icon-green { background: #16a34a; }
.icon-teal { background: #0d9488; }
.icon-purple { background: #8b5cf6; }
.icon-indigo { background: #6366f1; }
.icon-orange { background: #ea580c; }
.icon-amber { background: #d97706; }
.icon-rose { background: #e11d48; }
.icon-emerald { background: #059669; }
.icon-slate { background: #64748b; }

/* ===== Card Content ===== */
.card-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
}

.card-title {
  font-weight: 600;
  font-size: 0.9375rem;
  color: #f1f5f9;
  display: block;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.card-subtitle {
  font-size: 0.8125rem;
  color: #94a3b8;
  display: block;
}

.card-status {
  font-size: 0.75rem;
  font-weight: 500;
  display: flex;
  align-items: center;
}

.status-running {
  color: #fbbf24;
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.status-done {
  color: #34d399;
  font-weight: 600;
}

.status-pending {
  color: #64748b;
}

/* ===== Spinner ===== */
.spinner {
  width: 0.75rem;
  height: 0.75rem;
  border: 2px solid #fbbf24;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ===== Forecast Card ===== */
.btn-forecast-primary {
  background: rgba(251, 191, 36, 0.15);
  border: 1px solid rgba(251, 191, 36, 0.4);
}

.btn-forecast-primary:hover:not(:disabled) {
  background: rgba(251, 191, 36, 0.2);
  border-color: rgba(251, 191, 36, 0.6);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 0 20px rgba(251, 191, 36, 0.2);
}

/* ===== Base Buttons ===== */
.btn-etl,
.btn-fetch {
  background: transparent;
}

.btn-forecast {
  background: rgba(251, 191, 36, 0.15);
  border: 1px solid rgba(251, 191, 36, 0.4);
}

.btn-forecast:hover:not(:disabled) {
  background: rgba(251, 191, 36, 0.2);
  border-color: rgba(251, 191, 36, 0.6);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 0 20px rgba(251, 191, 36, 0.2);
}

/* ===== Animations ===== */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.stepper-step {
  animation: fadeInUp 0.6s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

  .stepper-step:nth-child(1) { animation-delay: 0s; }
  .stepper-step:nth-child(2) { animation-delay: 0.15s; }
  .stepper-step:nth-child(3) { animation-delay: 0.3s; }
  .stepper-step:nth-child(4) { animation-delay: 0.45s; }
  .stepper-step:nth-child(5) { animation-delay: 0.6s; }

/* ===== Responsive ===== */
@media (max-width: 1024px) {
  .action-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .action-grid.gapless {
    max-width: 100%;
  }
}

@media (max-width: 640px) {
  .action-grid {
    grid-template-columns: 1fr;
  }
  
  .action-grid.gapless {
    grid-template-columns: 1fr;
  }
  
  .dashboard-section {
    padding: 1.25rem;
  }
  
  .stepper-title {
    flex-direction: column;
    align-items: flex-start;
  }
}

/* ===== Fade Transition ===== */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
