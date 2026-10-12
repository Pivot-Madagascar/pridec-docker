<template>
  <section class="job-logs-section space-y-2">
    <div class="flex items-center justify-between gap-4">
      <h3 class="flex items-center gap-2 text-sm font-semibold text-gray-100">
        Logs
        <span v-if="live" class="live-badge rounded bg-green-900 px-2 py-0.5 text-xs text-green-300">● Live</span>
      </h3>
      <button
        class="rounded-md px-3 py-1 text-sm bg-gray-700 text-gray-300 hover:bg-gray-600"
        :disabled="jobLogsLoading"
        @click="store.fetchJobLogs(jobId)"
      >
        {{ jobLogsLoading ? 'Loading...' : 'Refresh logs' }}
      </button>
    </div>
    <JobLogs :logs="displayedLogs" :loading="jobLogsLoading" :error="jobLogsError" />
  </section>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useTrackingStore } from '@/stores/useTrackingStore'
import type { JobLogs as JobLogsData } from '@/services/api'
import JobLogs from './JobLogs.vue'
import { useWebSocketLogger } from '@/composables/useWebSocketLogger'

const props = defineProps<{ jobId: string }>()

const store = useTrackingStore()
const { jobLogs, jobLogsLoading, jobLogsError } = storeToRefs(store)

// Job logs: loaded over HTTP (and on Refresh). A pending or running job is then
// followed live over the log WebSocket until it ends; the final state is reloaded once.
const ws = useWebSocketLogger()
const live = ref(false)

async function openLogs(jobId: string) {
  stopLive()
  jobLogs.value = null  // never show the previous job's logs while loading
  await store.fetchJobLogs(jobId)
  const status = jobLogs.value?.status
  if (props.jobId === jobId && (status === 'pending' || status === 'running')) {
    live.value = true
    ws.connect(jobId)
  }
}

function stopLive() {
  live.value = false
  ws.disconnect()
  ws.clearLogs()
}

watch(() => props.jobId, openLogs, { immediate: true })
onUnmounted(stopLive)

watch(ws.isCompleted, (done) => {
  if (done && live.value) {
    stopLive()
    store.fetchJobLogs(props.jobId)
  }
})

// While live, the WebSocket's history + new entries and status replace the HTTP snapshot.
const displayedLogs = computed<JobLogsData | null>(() => {
  if (!jobLogs.value) return null
  if (!live.value) return jobLogs.value
  return {
    ...jobLogs.value,
    status: ws.status.value || jobLogs.value.status,
    message: ws.statusMessage.value || jobLogs.value.message,
    logs: ws.combinedLogs.value || jobLogs.value.logs,
  }
})
</script>
