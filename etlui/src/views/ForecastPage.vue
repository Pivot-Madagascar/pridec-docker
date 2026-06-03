<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-3xl font-bold text-[#131921] dark:text-white">Forecast Pipeline</h1>
    </div>

    <div class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 bg-gradient-to-br from-purple-600 to-indigo-700 rounded-lg flex items-center justify-center text-white font-bold">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <h2 class="text-xl font-semibold text-gray-900 dark:text-white">ML Forecasting</h2>
      </div>

      <p class="text-gray-600 dark:text-gray-400 mb-6">
        Configure and run the malaria forecasting pipeline. Ensure all required data has been imported before running.
      </p>

      <!-- Configuration Inputs -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Config Path</label>
          <input
            v-model="configPath"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-yellow-400 focus:border-transparent"
            placeholder="input/config.json"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">External Data Path</label>
          <input
            v-model="externalDataPath"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-yellow-400 focus:border-transparent"
            placeholder="input/external_data.csv"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Climate Data Path</label>
          <input
            v-model="climateDataPath"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-yellow-400 focus:border-transparent"
            placeholder="input/climate_data.json"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Disease Data Path</label>
          <input
            v-model="diseaseDataPath"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-yellow-400 focus:border-transparent"
            placeholder="input/disease_data.json"
          />
        </div>
      </div>

      <!-- Run Button -->
      <button
        @click="runForecast"
        :disabled="isRunning"
        class="w-full md:w-auto px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-700 hover:from-purple-700 hover:to-indigo-800 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
      >
        <svg v-if="isRunning" class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        {{ isRunning ? 'Starting Forecast...' : 'Run Forecast' }}
      </button>

      <!-- Job ID Display -->
      <transition name="fade">
        <div v-if="jobId" class="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-blue-800 dark:text-blue-300">Job Created</p>
              <p class="text-xs text-blue-600 dark:text-blue-400 font-mono">{{ jobId }}</p>
            </div>
            <router-link
              :to="`/status/${jobId}`"
              class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md transition-colors"
            >
              View Status
            </router-link>
          </div>
        </div>
      </transition>

      <!-- Messages -->
      <transition name="fade">
        <div v-if="message" class="mt-4 p-4 rounded-lg" :class="messageType === 'success' ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-800 dark:text-green-300' : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-300'">
          {{ message }}
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import axios from 'axios'

const isRunning = ref(false)
const jobId = ref('')
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const configPath = ref('input/config.json')
const externalDataPath = ref('input/external_data.csv')
const climateDataPath = ref('input/climate_data.json')
const diseaseDataPath = ref('input/disease_data.json')

const runForecast = async () => {
  isRunning.value = true
  message.value = ''
  jobId.value = ''

  try {
    const response = await axios.post('/forecast/', {
      config_path: configPath.value,
      external_data_path: externalDataPath.value,
      climate_data_path: climateDataPath.value,
      disease_data_path: diseaseDataPath.value,
      orgUnit_poly_path: 'input/orgUnit_poly.geojson'
    })

    message.value = response.data.message || 'Forecast job started'
    messageType.value = 'success'
    jobId.value = response.data.job_id || ''
  } catch (err) {
    console.error('Forecast error:', err)
    message.value = err.response?.data?.detail || err.response?.data?.message || 'Failed to start forecast'
    messageType.value = 'error'
  } finally {
    isRunning.value = false
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
