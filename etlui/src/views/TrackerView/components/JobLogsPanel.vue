<template>
  <section data-test="job-logs-section" class="job-logs-section space-y-2">
    <div class="flex items-center justify-between gap-4">
      <h3 class="flex items-center gap-2 text-sm font-semibold text-foreground">
        Logs
        <Badge v-if="live" data-test="live-badge" class="border-transparent bg-success/15 text-success">● Live</Badge>
      </h3>
      <Button variant="secondary" size="sm" :disabled="jobLogsLoading" @click="store.fetchJobLogs(jobId)">
        {{ jobLogsLoading ? 'Loading...' : 'Refresh logs' }}
      </Button>
    </div>
    <div v-if="jobLogsError" class="rounded-lg border border-destructive/40 bg-destructive/15 p-3 text-sm text-destructive">
      {{ jobLogsError }}
    </div>
    <template v-else-if="displayedLogs">
      <div class="flex flex-wrap items-center gap-3 text-sm">
        <span class="text-muted-foreground">Status</span>
        <span class="rounded px-2 py-0.5 text-xs font-semibold" :class="statusColor(displayedLogs.status)">
          {{ displayedLogs.status ?? 'unknown (record expired)' }}
        </span>
        <span v-if="displayedLogs.message" class="text-foreground">{{ displayedLogs.message }}</span>
      </div>
      <pre class="max-h-[60vh] overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-muted p-3 font-mono text-xs text-foreground">{{ displayedLogs.logs || 'No logs yet.' }}</pre>
    </template>
    <p v-else-if="jobLogsLoading" class="text-sm text-muted-foreground">Loading logs...</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useTrackingStore } from '@/stores/useTrackingStore'
import type { JobLogs } from '@/services/api'
import { statusColor } from '@/utils/status'
import { useWebSocketLogger } from '@/composables/useWebSocketLogger'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

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
const displayedLogs = computed<JobLogs | null>(() => {
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
