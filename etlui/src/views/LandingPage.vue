<template>
  <div class="space-y-8">
    <!-- Hero Section -->
    <HeroSection />

    <!-- Quick Actions -->
    <QuickActions 
      :loadingClimate="loadingClimate"
      :loadingDisease="loadingDisease"
      :loadingGeoJSON="loadingGeoJSON"
      @run-forecast="navigateTo('/forecast')"
      @fetch-climate="fetchClimate"
      @fetch-disease="fetchDisease"
      @fetch-geojson="fetchGeoJSON"
    />

    <!-- ETL Pipeline -->
    <ETLPipeline 
      :loading="loading"
      :results="results"
      @trigger-etl="triggerETL"
    />

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
import QuickActions from './components/QuickActions.vue'
import ETLPipeline from './components/ETLPipeline.vue'
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

const fetchClimate = async () => {
  loadingClimate.value = true
  try {
    await api.post('/fetch_climate')
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
    await api.post('/fetch_disease')
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
    await api.post('/fetch_geojson')
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