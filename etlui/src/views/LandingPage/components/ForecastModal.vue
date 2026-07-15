<template>
  <transition name="modal-fade">
    <div v-if="modelValue" class="modal-backdrop" @click="closeModal">
      <div class="modal-container" @click.stop>
        <div class="modal-content">
          <div class="modal-header">
            <h2 class="modal-title">Forecast Pipeline</h2>
            <button class="modal-close" @click="closeModal">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <p class="modal-description text-white mb-6">
            Configure and run the disease forecasting pipeline. Ensure all required data has been imported before running.
          </p>

          <div class="form-grid">
            <div>
              <label class="form-label">Config Valid Path</label>
              <input
                v-model="configValidPath"
                type="text"
                class="form-input"
                placeholder="input/config_valid.json"
              />
            </div>
            <div>
              <label class="form-label">Input Valid Path</label>
              <input
                v-model="inputValidPath"
                type="text"
                class="form-input"
                placeholder="input/input_valid.json"
              />
            </div>
            <div class="md:col-span-2">
              <label class="form-label">Polygon Valid Path</label>
              <input
                v-model="polygonValidPath"
                type="text"
                class="form-input"
                placeholder="input/polygon_valid.geojson"
              />
            </div>
          </div>

          <button
            @click="runForecast"
            :disabled="isRunning"
            class="btn-primary"
          >
            <svg v-if="isRunning" class="spinner-sm" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" class="icon-sm" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {{ isRunning ? 'Starting Forecast...' : 'Run Forecast' }}
          </button>

          <transition name="fade">
            <div v-if="jobId" class="job-confirmation">
              <div class="job-info">
                <p class="job-label text-sm font-medium">Job Created</p>
                <p class="job-id text-xs font-mono">{{ jobId }}</p>
              </div>
            </div>
          </transition>

          <transition name="fade">
            <div v-if="message" class="message-box" :class="messageType === 'success' ? 'message-success' : 'message-error'">
              {{ message }}
            </div>
          </transition>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '@/services/api'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'job-created': [jobId: string]
}>()

const isRunning = ref(false)
const jobId = ref('')
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const configValidPath = ref('input/config_valid.json')
const inputValidPath = ref('input/input_valid.json')
const polygonValidPath = ref('input/polygon_valid.geojson')

const closeModal = () => {
  emit('update:modelValue', false)
  jobId.value = ''
  message.value = ''
}

const runForecast = async () => {
  isRunning.value = true
  message.value = ''
  jobId.value = ''

  try {
    const response = await api.post('/forecast/', {
      config_valid_path: configValidPath.value,
      input_valid_path: inputValidPath.value,
      polygon_valid_path: polygonValidPath.value,
    })

    message.value = response.data.message || 'Forecast job started'
    messageType.value = 'success'
    jobId.value = response.data.job_id || ''
    emit('job-created', jobId.value)
  } catch (err: any) {
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

/* ===== Modal Backdrop ===== */
.modal-backdrop {
  @apply fixed inset-0 bg-black/70 flex items-center justify-center z-50;
}

/* ===== Modal Container ===== */
.modal-container {
  @apply max-w-2xl w-full mx-4;
}

.modal-content {
  @apply bg-[#0f172a] border border-white/10 rounded-xl p-8 shadow-2xl;
}

/* ===== Modal Header ===== */
.modal-header {
  @apply flex items-center justify-between mb-6 pb-4 border-b border-white/10;
}

.modal-title {
  @apply text-2xl font-bold text-white;
}

.modal-close {
  @apply p-2 rounded-lg bg-white/5 border border-white/10 text-white hover:text-white hover:bg-white/20 transition-colors;
}

/* ===== Form ===== */
.form-grid {
  @apply grid grid-cols-1 md:grid-cols-2 gap-4 mb-6;
}

.form-label {
  @apply block text-sm font-medium text-white mb-2;
}

.form-input {
  @apply w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500 transition-colors;
}

/* ===== Buttons ===== */
.btn-primary {
  @apply w-full flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed;
}

.btn-primary:disabled {
  @apply opacity-50 cursor-not-allowed;
}

/* ===== Icons ===== */
.icon-sm {
  @apply w-5 h-5;
}

.spinner-sm {
  @apply w-5 h-5 animate-spin;
}

.spinner-sm circle {
  @apply opacity-25;
}

.spinner-sm path {
  @apply opacity-75;
}

/* ===== Messages ===== */
.message-box {
  @apply mt-4 p-4 rounded-lg text-white;
}

.message-success {
  @apply bg-green-900/30 text-white border border-green-500/30;
}

.message-error {
  @apply bg-red-900/30 text-white border border-red-500/30;
}

/* ===== Job Confirmation ===== */
.job-confirmation {
  @apply mt-4 p-4 bg-blue-900/20 border border-blue-500/30 rounded-lg;
}

.job-info {
  @apply flex flex-col gap-1;
}

.job-label {
  @apply text-white font-medium;
}

.job-id {
  @apply text-white font-mono;
}

/* ===== Transitions ===== */
.modal-fade-enter-active,
.modal-fade-leave-active {
  @apply transition-opacity duration-300;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  @apply opacity-0;
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