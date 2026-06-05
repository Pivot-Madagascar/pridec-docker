<template>
  <div class="space-y-6">
    <div class="flex-row-center-between">
      <h1 class="heading-primary">Forecast Pipeline</h1>
    </div>

    <div class="card card-padded">
      <div class="card-header">
        <div class="card-header-icon">
          <svg xmlns="http://www.w3.org/2000/svg" class="icon-md" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <h2 class="card-header-title">ML Forecasting</h2>
      </div>

      <p class="card-description">
        Configure and run the malaria forecasting pipeline. Ensure all required data has been imported before running.
      </p>

      <!-- Configuration Inputs -->
      <div class="grid-cols-2-md gap-4 mb-6">
        <div>
          <label class="form-label">Config Path</label>
          <input
            v-model="configPath"
            type="text"
            class="form-input"
            placeholder="input/config.json"
          />
        </div>
        <div>
          <label class="form-label">External Data Path</label>
          <input
            v-model="externalDataPath"
            type="text"
            class="form-input"
            placeholder="input/external_data.csv"
          />
        </div>
        <div>
          <label class="form-label">Climate Data Path</label>
          <input
            v-model="climateDataPath"
            type="text"
            class="form-input"
            placeholder="input/climate_data.json"
          />
        </div>
        <div>
          <label class="form-label">Disease Data Path</label>
          <input
            v-model="diseaseDataPath"
            type="text"
            class="form-input"
            placeholder="input/disease_data.json"
          />
        </div>
      </div>

      <!-- Run Button -->
      <button
        @click="runForecast"
        :disabled="isRunning"
        class="btn-primary"
      >
        <svg v-if="isRunning" class="spinner-sm" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" class="icon-sm mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        {{ isRunning ? 'Starting Forecast...' : 'Run Forecast' }}
      </button>

      <!-- Job ID Display -->
      <transition name="fade">
        <div v-if="jobId" class="job-confirmation">
          <div class="flex-row-center-between">
            <div>
              <p class="text-sm font-medium text-blue-800 dark:text-blue-300">Job Created</p>
              <p class="text-xs text-blue-600 dark:text-blue-400 font-mono">{{ jobId }}</p>
            </div>
            <router-link
              :to="`/status/${jobId}`"
              class="btn-link"
            >
              View Status
            </router-link>
          </div>
        </div>
      </transition>

      <!-- Messages -->
      <transition name="fade">
        <div v-if="message" class="message-box" :class="messageType === 'success' ? 'message-success' : 'message-error'">
          {{ message }}
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '@/services/api'

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
    const response = await api.post('/forecast/', {
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
@reference "tailwindcss";

.message-box {
  @apply mt-4 p-4 rounded-lg;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>