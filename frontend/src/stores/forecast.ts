import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

interface OutputFile {
  filename: string
  file_path: string
  file_size_bytes: number
  last_modified: string
  available: boolean
}

interface ForecastOutputStatus {
  output_files: OutputFile[]
  total_files: number
  forecast_report_available: boolean
  output_directory: string
}

export const useForecastStore = defineStore('forecast', () => {
  const outputStatus = ref<ForecastOutputStatus | null>(null)
  const isLoading = ref(false)
  const lastChecked = ref<Date | null>(null)

  const hasOutput = computed(() => {
    return (outputStatus.value?.total_files || 0) > 0
  })

  const hasForecastReport = computed(() => {
    return outputStatus.value?.forecast_report_available || false
  })

  const outputFiles = computed(() => {
    return outputStatus.value?.output_files || []
  })

  const checkOutputStatus = async () => {
    isLoading.value = true
    try {
      const token = localStorage.getItem('token')
      const headers = token ? { Authorization: `Bearer ${token}` } : {}

      const response = await axios.get('/api/forecast/output/status', { headers })

      if (response.data.success) {
        outputStatus.value = response.data.data
        lastChecked.value = new Date()
      }
    } catch (error) {
      console.error('Error checking forecast output status:', error)
      // Reset status on error
      outputStatus.value = {
        output_files: [],
        total_files: 0,
        forecast_report_available: false,
        output_directory: 'output'
      }
    } finally {
      isLoading.value = false
    }
  }

  const refreshStatus = async () => {
    await checkOutputStatus()
  }

  return {
    outputStatus,
    isLoading,
    lastChecked,
    hasOutput,
    hasForecastReport,
    outputFiles,
    checkOutputStatus,
    refreshStatus
  }
})