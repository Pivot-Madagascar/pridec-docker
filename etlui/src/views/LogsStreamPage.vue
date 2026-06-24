<template>
  <div class="space-y-6">
    <div class="flex-row-center-between">
      <h1 class="heading-primary">ETL Logs Live</h1>
      <div class="flex-row-center space-x-3">
        <span
          v-if="jobId"
          class="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold"
          :class="statusBadgeClass"
        >
          <span class="w-2 h-2 rounded-full mr-2" :class="statusDotClass"></span>
          {{ status || 'Idle' }}
        </span>
        <button
          class="btn-link-secondary"
          @click="reset"
        >
          Reset
        </button>
      </div>
    </div>

    <p class="text-sm text-gray-400 max-w-3xl">
      Connect to an ETL job via WebSocket to stream logs in real time. Enter a job ID below to start tracking.
    </p>

    <div class="card card-padded">
      <div class="flex-row-center-between gap-4 flex-wrap">
        <div class="flex-row-center flex-1 space-x-3 min-w-[300px]">
          <input
            v-model="jobIdInput"
            type="text"
            class="form-input font-mono"
            placeholder="Enter job ID (e.g. import_gee_a1b2c3d4)"
            @keyup.enter="start"
            :disabled="connected"
          />
          <button
            class="btn-primary"
            :disabled="!jobIdInput || connected || (!isCompleted && currentJobId !== jobIdInput)"
            @click="start"
          >
            <svg v-if="connecting" class="animate-spin h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ connected ? 'Connected' : connecting ? 'Connecting...' : 'Connect' }}
          </button>
          <button
            v-if="connected"
            class="btn-link-secondary"
            @click="stop"
          >
            Disconnect
          </button>
        </div>
        <div v-if="connectionError" class="text-sm text-red-400">
          {{ connectionError }}
        </div>
      </div>

      <div v-if="statusMessage" class="mt-4 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
        <p class="text-sm text-blue-800 dark:text-blue-300">{{ statusMessage }}</p>
      </div>
    </div>

    <div class="card card-padded">
      <div class="flex-row-center-between mb-4">
        <h2 class="heading-tertiary text-gray-900 dark:text-white">Log Output</h2>
        <div class="flex-row-center space-x-2">
          <span class="text-xs text-gray-500">Lines: {{ lineCount }}</span>
          <button
            v-if="lineCount > 0"
            class="text-xs text-blue-400 hover:text-blue-300"
            @click="scrollToBottom"
          >
            Scroll ↓
          </button>
          <button
            v-if="lineCount > 0"
            class="text-xs text-gray-400 hover:text-gray-300"
            @click="clear"
          >
            Clear
          </button>
        </div>
      </div>

      <div
        ref="logContainer"
        class="log-container"
      >
        <template v-if="history && !logs.length && !connected">
          <pre class="text-sm text-gray-300 font-mono whitespace-pre-wrap">{{ history }}</pre>
        </template>
        <template v-else-if="combinedLogs">
          <pre class="text-sm text-green-400 font-mono whitespace-pre-wrap">{{ combinedLogs }}</pre>
        </template>
        <template v-else>
          <p class="text-sm text-gray-500 text-center py-8">
            Connect to a job to start streaming logs.
          </p>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
@reference "tailwindcss";

.log-container {
  @apply bg-[#1a1a1a] rounded-lg p-4 h-[500px] overflow-y-auto border border-gray-800;
}

.status-badge-success {
  @apply bg-green-50 text-green-800 border border-green-200;
}

.status-badge-running {
  @apply bg-yellow-50 text-yellow-800 border border-yellow-200;
}

.status-badge-error {
  @apply bg-red-50 text-red-800 border border-red-200;
}

.status-badge-unknown {
  @apply bg-gray-50 text-gray-800 border border-gray-200;
}

.log-line-enter-active,
.log-line-leave-active {
  transition: all 0.3s ease;
}

.log-line-enter-from,
.log-line-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useWebSocketLogger } from '@/composables/useWebSocketLogger'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8111'

const {
  logs,
  history,
  status,
  statusMessage,
  connected,
  connectionError,
  connect,
  disconnect,
  clearLogs,
  isRunning,
  isCompleted,
  combinedLogs,
} = useWebSocketLogger({ baseUrl: apiBaseUrl })

const jobIdInput = ref('')
const currentJobId = ref('')
const connecting = ref(false)
const logContainer = ref<HTMLElement | null>(null)
const lineCount = ref(0)

const statusDotClass = computed(() => {
  if (isRunning.value) return 'bg-yellow-500'
  if (status.value === 'success') return 'bg-green-500'
  if (status.value === 'error') return 'bg-red-500'
  return 'bg-gray-400'
})

const statusBadgeClass = computed(() => {
  if (isRunning.value) return 'status-badge-running'
  if (status.value === 'success') return 'status-badge-success'
  if (status.value === 'error') return 'status-badge-error'
  return 'status-badge-unknown'
})

watch(combinedLogs, (val) => {
  if (!val) {
    lineCount.value = 0
    return
  }
  lineCount.value = val.split('\n').filter(l => l.trim()).length
  nextTick(() => scrollToBottom())
})

watch(connected, (val) => {
  if (val) {
    connecting.value = false
  }
})

async function start() {
  const jobId = jobIdInput.value.trim()
  if (!jobId) return
  currentJobId.value = jobId
  connecting.value = true
  connect(jobId)
}

function stop() {
  disconnect()
}

function reset() {
  disconnect()
  jobIdInput.value = ''
  currentJobId.value = ''
  clearLogs()
  lineCount.value = 0
}

function clear() {
  clearLogs()
  lineCount.value = 0
}

function scrollToBottom() {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}
</script>
