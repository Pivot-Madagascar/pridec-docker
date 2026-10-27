<template>
  <div class="space-y-6">
    <div class="flex-row-center-between">
      <h1 class="heading-primary">ETL Logs Live</h1>
      <div class="flex-row-center space-x-3">
        <Badge v-if="currentJobId" variant="outline" class="px-3 py-1" :class="statusBadgeClass">
          <span class="size-2 rounded-full" :class="statusDotClass"></span>
          {{ status || 'Idle' }}
        </Badge>
        <Button variant="secondary" @click="reset">Reset</Button>
      </div>
    </div>

    <p class="text-sm text-muted-foreground max-w-3xl">
      Connect to an ETL job via WebSocket to stream logs in real time. Enter a job ID below to start tracking.
    </p>

    <Card>
      <CardContent>
      <div class="flex-row-center-between gap-4 flex-wrap">
        <div class="flex-row-center flex-1 space-x-3 min-w-75">
          <Input
            v-model="jobIdInput"
            type="text"
            class="font-mono"
            aria-label="Job ID"
            placeholder="Enter job ID (e.g. import_gee_a1b2c3d4)"
            @keyup.enter="start"
            :disabled="connected || !!route.query.jobId"
          />
          <Button
            :disabled="!jobIdInput || connected || (!isCompleted && currentJobId !== jobIdInput)"
            @click="start"
          >
            <LoaderCircle v-if="connecting" class="animate-spin" aria-hidden="true" />
            {{ connected ? 'Connected' : connecting ? 'Connecting...' : 'Connect' }}
          </Button>
          <Button v-if="connected" variant="secondary" @click="disconnect">Disconnect</Button>
        </div>
        <div v-if="connectionError" class="text-sm text-destructive">
          {{ connectionError }}
        </div>
      </div>

      <div v-if="statusMessage" class="mt-4 p-3 rounded-lg bg-primary/15 border border-primary/40">
        <p class="text-sm text-primary">{{ statusMessage }}</p>
      </div>
      </CardContent>
    </Card>

    <Card>
      <CardContent>
      <div class="flex-row-center-between mb-4">
        <h2 class="heading-tertiary text-foreground">Log Output</h2>
        <div class="flex-row-center space-x-2">
          <span class="text-xs text-muted-foreground">Lines: {{ lineCount }}</span>
          <Button v-if="lineCount > 0" variant="link" size="xs" @click="scrollToBottom">Scroll ↓</Button>
          <Button v-if="lineCount > 0" variant="ghost" size="xs" @click="clearLogs">Clear</Button>
        </div>
      </div>

      <div
        ref="logContainer"
        class="log-container"
      >
        <template v-if="history && !logs.length && !connected">
          <pre class="text-sm text-foreground font-mono whitespace-pre-wrap">{{ history }}</pre>
        </template>
        <template v-else-if="combinedLogs">
          <pre class="text-sm text-foreground font-mono whitespace-pre-wrap">{{ combinedLogs }}</pre>
        </template>
        <template v-else>
          <p class="text-sm text-muted-foreground text-center py-8">
            Connect to a job to start streaming logs.
          </p>
        </template>
      </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { LoaderCircle } from '@lucide/vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useWebSocketLogger } from '@/composables/useWebSocketLogger'

const route = useRoute()

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
} = useWebSocketLogger()

const jobIdInput = ref('')
const currentJobId = ref('')
const connecting = ref(false)
const logContainer = ref<HTMLElement | null>(null)
const lineCount = computed(() => combinedLogs.value.split('\n').filter(l => l.trim()).length)

watch(
  () => route.query.jobId,
  (jobId) => {
    if (typeof jobId === 'string' && jobId && !connected.value) {
      jobIdInput.value = jobId
      currentJobId.value = jobId
      connecting.value = true
      connect(jobId)
    }
  },
  { immediate: true }
)

const statusDotClass = computed(() => {
  if (isRunning.value) return 'bg-warning'
  if (status.value === 'success') return 'bg-success'
  if (status.value === 'error') return 'bg-destructive'
  return 'bg-muted-foreground'
})

const statusBadgeClass = computed(() => {
  if (isRunning.value) return 'status-badge-running'
  if (status.value === 'success') return 'status-badge-success'
  if (status.value === 'error') return 'status-badge-error'
  return 'status-badge-unknown'
})

watch(combinedLogs, (val) => val && nextTick(scrollToBottom))

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

function reset() {
  disconnect()
  jobIdInput.value = ''
  currentJobId.value = ''
  clearLogs()
}

function scrollToBottom() {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}
</script>

<style scoped>
@reference "../styles/base.css";

.log-container {
  @apply bg-muted rounded-lg p-4 h-[500px] overflow-y-auto border border-border;
}

.status-badge-success {
  @apply bg-success/15 text-success border border-success/40;
}

.status-badge-running {
  @apply bg-warning/15 text-warning border border-warning/40;
}

.status-badge-error {
  @apply bg-destructive/15 text-destructive border border-destructive/40;
}

.status-badge-unknown {
  @apply bg-muted text-foreground border border-border;
}
</style>