<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-3xl font-bold text-white">Reports</h1>
    </div>

    <div class="bg-gray-800 rounded-lg border border-gray-700 p-6">
      <div v-if="!forecastStore.hasForecastReport" class="text-center py-12">
        <div class="w-16 h-16 bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h3 class="text-xl font-semibold text-white mb-2">No Reports Available</h3>
        <p class="text-gray-400 mb-6">Run a forecast to generate reports.</p>
        <router-link
          to="/forecasting"
          class="inline-flex items-center px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white font-medium rounded-lg transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Go to Forecasting
        </router-link>
      </div>

      <div v-else>
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-semibold text-white">Generated Reports</h2>
          <button
            @click="refreshReports"
            class="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
          >
            Refresh
          </button>
        </div>

        <!-- Forecast Report -->
        <div class="mb-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-medium text-white">Forecast Report</h3>
            <div class="flex space-x-2">
              <button
                @click="viewReportInNewTab"
                class="p-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                title="Open in New Tab"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </button>
              <button
                @click="downloadReport"
                class="p-2 bg-green-600 hover:bg-green-700 text-white rounded transition-colors"
                title="Download"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </button>
            </div>
          </div>

          <div class="bg-gray-900 rounded-lg border border-gray-600 p-4">
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 bg-green-900/30 rounded flex items-center justify-center">
                <span class="text-xs">📄</span>
              </div>
              <div>
                <p class="text-white font-medium">forecast_report.html</p>
                <p class="text-gray-400 text-sm">
                  Last modified: {{ getReportFile()?.last_modified ? formatDate(getReportFile()!.last_modified) : 'Unknown' }}
                  • Size: {{ formatFileSize(getReportFile()?.file_size_bytes || 0) }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Other Output Files -->
        <div v-if="otherFiles.length > 0">
          <h3 class="text-lg font-medium text-white mb-4">Other Output Files</h3>
          <div class="space-y-3">
            <div
              v-for="file in otherFiles"
              :key="file.filename"
              class="p-4 rounded-lg bg-gray-700 border border-gray-600"
            >
              <div class="flex justify-between items-start">
                <div class="flex-1">
                  <div class="flex items-center space-x-3">
                    <div class="w-8 h-8 bg-blue-900/30 rounded flex items-center justify-center">
                      <span class="text-xs">{{ getFileIcon(file.filename) }}</span>
                    </div>
                    <div>
                      <p class="text-white font-medium">{{ file.filename }}</p>
                      <p class="text-gray-400 text-sm">
                        {{ formatFileSize(file.file_size_bytes) }}
                        • {{ formatDate(file.last_modified) }}
                      </p>
                    </div>
                  </div>
                </div>
                <button
                  @click="downloadFile(file.filename)"
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
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useForecastStore } from '@/stores/forecast'
import axios from 'axios'

const forecastStore = useForecastStore()

const otherFiles = computed(() => {
  return forecastStore.outputFiles.filter(file => file.filename !== 'forecast_report.html')
})

const getReportFile = () => {
  return forecastStore.outputFiles.find(file => file.filename === 'forecast_report.html')
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString()
}

const getFileIcon = (filename: string) => {
  const ext = filename.toLowerCase().split('.').pop()
  switch (ext) {
    case 'json': return '📄'
    case 'html': return '🌐'
    case 'csv': return '📊'
    default: return '📄'
  }
}

const refreshReports = async () => {
  await forecastStore.refreshStatus()
}

const viewReportInNewTab = async () => {
  try {
    const token = localStorage.getItem('token')
    const headers = token ? { Authorization: `Bearer ${token}` } : {}

    const response = await axios.get('/api/forecast/output/forecast_report.html', {
      headers,
      responseType: 'blob'
    })

    // Create a blob URL for the HTML content
    const blob = new Blob([response.data], { type: 'text/html' })
    const blobUrl = URL.createObjectURL(blob)

    // Open the blob URL in a new tab
    window.open(blobUrl, '_blank')

    // Clean up the blob URL after a delay to allow the tab to load
    setTimeout(() => {
      URL.revokeObjectURL(blobUrl)
    }, 1000)

  } catch (error) {
    console.error('Error opening report in new tab:', error)
    // Fallback to direct API call
    window.open('/api/forecast/output/forecast_report.html', '_blank')
  }
}

const downloadReport = async () => {
  try {
    const token = localStorage.getItem('token')
    const headers = token ? { Authorization: `Bearer ${token}` } : {}

    const response = await axios.get('/api/forecast/output/forecast_report.html', {
      headers,
      responseType: 'blob'
    })

    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'forecast_report.html')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Error downloading report:', error)
  }
}

const downloadFile = async (filename: string) => {
  try {
    const token = localStorage.getItem('token')
    const headers = token ? { Authorization: `Bearer ${token}` } : {}

    const response = await axios.get(`/api/forecast/output/${filename}`, {
      headers,
      responseType: 'blob'
    })

    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Error downloading file:', error)
  }
}

onMounted(async () => {
  await forecastStore.checkOutputStatus()
})
</script>