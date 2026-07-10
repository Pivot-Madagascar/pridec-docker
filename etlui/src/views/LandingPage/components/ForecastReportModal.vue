<template>
  <transition name="modal-fade">
    <div v-if="modelValue" class="modal-backdrop" @click="closeModal">
      <div class="modal-container" @click.stop>
        <div class="modal-header">
          <h2 class="modal-title">Forecast Report</h2>
          <div class="flex items-center gap-2">
            <button class="modal-refresh" @click="fetchReport" :disabled="loading">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" :class="{ 'animate-spin': loading }">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h5M20 20v-5h-5M4 4l5 5m11 11l-5-5" />
              </svg>
              <span>Refresh</span>
            </button>
            <button class="modal-close" @click="closeModal">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div class="modal-body">
          <iframe
            v-if="reportContent"
            :srcdoc="reportContent"
            class="report-iframe"
            title="Forecast Report"
          ></iframe>
          <div v-else-if="loading" class="report-loading">
            <svg class="spinner-lg" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p>Loading report...</p>
          </div>
          <div v-else class="report-error">
            <p>{{ errorMessage }}</p>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const reportContent = ref('')
const loading = ref(false)
const errorMessage = ref('')

const closeModal = () => {
  emit('update:modelValue', false)
}

const fetchReport = async () => {
  loading.value = true
  reportContent.value = ''
  errorMessage.value = ''
  
  try {
    const response = await api.get('/output/forecast_report.html')
    reportContent.value = response.data
  } catch (err: any) {
    if (err.response?.status === 404) {
      errorMessage.value = 'Forecast report not found. Run the forecast step first.'
    } else {
      errorMessage.value = 'Failed to load report. Please try again.'
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchReport()
})
</script>

<style scoped>
@reference "tailwindcss";

.modal-backdrop {
  @apply fixed inset-0 bg-black/90 z-50;
}

.modal-container {
  @apply fixed inset-0 w-screen h-screen;
}

.modal-header {
  @apply flex items-center justify-between p-4 border-b border-white/10 bg-[#1e293b];
}

.modal-title {
  @apply text-2xl font-bold text-white;
}

.modal-close {
  @apply p-2 rounded-lg bg-white/5 border border-white/10 text-white hover:text-white hover:bg-white/20 transition-colors;
}

.modal-refresh {
  @apply p-2 rounded-lg bg-white/5 border border-white/10 text-white hover:text-white hover:bg-white/20 transition-colors flex items-center gap-2;
}

.modal-body {
  @apply flex-1 overflow-hidden;
  height: stretch;
}

.report-iframe {
  @apply w-full h-full border-none bg-white;
}

.report-loading {
  @apply flex flex-col items-center justify-center h-full text-white;
}

.spinner-lg {
  @apply w-12 h-12 animate-spin mb-4;
}

.report-error {
  @apply flex items-center justify-center h-full text-red-400;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  @apply transition-opacity duration-300;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  @apply opacity-0;
}
</style>