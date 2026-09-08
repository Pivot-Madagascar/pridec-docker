import { ref, reactive, computed } from 'vue'
import api from '@/services/api'
import { useForecastConfigStore } from '@/stores/forecastConfig'
import { useNotification } from '@/composables/useNotification'
import { useActivityLog } from '@/composables/useActivityLog'

export interface ActivityEntry {
  id: number
  action: string
  message: string
  time: string
  success: boolean
  jobId?: string
}

// États pour les actions de la grille d'importation (Data Import)
export const loading = reactive({
  import_gee: false,
  import_pivot_com: false,
  import_pivot_csb: false,
  build_analytics: false,
  calc_csb_alerts: false,
  update_key: false,
  post_forecast: false,
  validate_inputs: false
})

export const results = reactive({
  import_gee: false,
  import_pivot_com: false,
  import_pivot_csb: false,
  build_analytics: false,
  calc_csb_alerts: false,
  update_key: false,
  post_forecast: false,
  validate_inputs: false
})

// États pour l'étape de récupération des données (fetch_*)
export const loadingClimate = ref(false)
export const loadingDisease = ref(false)
export const loadingGeoJSON = ref(false)
export const refreshingReport = ref(false)

export const climateSuccess = ref(false)
export const diseaseSuccess = ref(false)
export const geojsonSuccess = ref(false)

export const forecastReportExists = ref(false)

// États pour la page principale
export const lastJobId = ref('')

export function useEtlPipeline() {
  const { showNotification } = useNotification()
  const { addActivity } = useActivityLog()

  const configIsValid = computed(() => {
    const forecastConfig = useForecastConfigStore()
    return forecastConfig.isValid
  })

  // Helper function to map fetch keys to state objects
  const getFetchState = (key: 'fetch_climate' | 'fetch_disease' | 'fetch_geojson') => {
    const map = {
      fetch_climate: { loading: loadingClimate, success: climateSuccess },
      fetch_disease: { loading: loadingDisease, success: diseaseSuccess },
      fetch_geojson: { loading: loadingGeoJSON, success: geojsonSuccess }
    }
    return map[key]
  }

  // Generic function to run fetch actions (common pattern: loading → API call → success/notification/activity)
  const runFetchAction = async (
    key: 'fetch_climate' | 'fetch_disease' | 'fetch_geojson',
    endpoint: string,
    payload?: Record<string, unknown>
  ) => {
    const state = getFetchState(key)
    
    state.loading.value = true
    state.success.value = false
    
    try {
      const response = await api.post(endpoint, payload)
      const jobId = response.data?.job_id || ''
      if (jobId) lastJobId.value = jobId
      
      // Notifications and activities are handled by callers
      
      state.success.value = true
      return { jobId, data: response.data }
    } catch (err) {
      state.success.value = false
      throw err
    } finally {
      state.loading.value = false
    }
  }

  // Generic ETL trigger for the remaining endpoints (import_gee, build_analytics, etc.)
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
      return { jobId, message: response.data.message }
    } catch (err) {
      showNotification(`Failed: ${endpoint}`, 'error')
      addActivity(
        endpoint.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        'ETL step failed',
        false
      )
      throw err
    } finally {
      loading[endpoint as keyof typeof loading] = false
    }
  }

  // Validate inputs endpoint
  const validateInputs = async (payload: any) => {
    loading.validate_inputs = true
    results.validate_inputs = false
    try {
      const response = await api.post('/validate_inputs', payload)
      const jobId = response.data?.job_id || ''
      if (jobId) lastJobId.value = jobId
      results.validate_inputs = true
      showNotification(response.data.message || 'Inputs validated', 'success')
      addActivity('Validate Inputs', response.data.message || 'Validation passed', true, jobId)
      return { jobId, message: response.data.message }
    } catch (err) {
      showNotification('Validation failed', 'error')
      addActivity('Validate Inputs', 'Validation failed', false)
      throw err
    } finally {
      loading.validate_inputs = false
    }
  }

  // Forecast report operations
  const checkForecastReportExists = async () => {
    refreshingReport.value = true
    try {
      const response = await api.get('/output/forecast_report.html/exists')
      forecastReportExists.value = response.data.exists
      showNotification('Report status refreshed', 'success')
      return forecastReportExists.value
    } catch {
      forecastReportExists.value = false
      showNotification('Failed to check report status', 'error')
      return false
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
      throw err
    }
  }

  // Fetch actions with specific notification messages
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

  const fetchDisease = async (forecastConfig: any) => {
    loadingDisease.value = true
    diseaseSuccess.value = false
    try {
      const response = await api.post('/fetch_disease', {
        disease_code: forecastConfig.diseaseCode,
        ou_level: forecastConfig.ouLevel
      })
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

  return {
    // États
    loading,
    results,
    loadingClimate,
    loadingDisease,
    loadingGeoJSON,
    refreshingReport,
    climateSuccess,
    diseaseSuccess,
    geojsonSuccess,
    forecastReportExists,
    lastJobId,
    configIsValid,
    
    // Fonctions
    triggerETL,
    validateInputs,
    checkForecastReportExists,
    resetReports,
    runFetchAction,
    fetchClimate,
    fetchDisease,
    fetchGeoJSON
  }
}