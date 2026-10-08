<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between gap-4">
      <h1 class="text-2xl font-bold text-gray-100">Request Tracking</h1>
      <div class="flex items-center gap-2">
        <input
          v-model="endpointFilter"
          type="text"
          placeholder="Filter by endpoint (e.g. /import_gee)"
          @keyup.enter="refresh"
          class="rounded-md border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
        />
        <button
          class="rounded-md px-4 py-1.5 text-sm bg-gray-800 text-gray-300 hover:bg-gray-700"
          @click="refresh"
          :disabled="loading"
        >
          {{ loading ? 'Loading...' : 'Refresh' }}
        </button>
      </div>
    </div>

    <div v-if="error" class="rounded-lg border border-red-900 bg-red-950 p-3 text-sm text-red-300">
      {{ error }}
    </div>

    <RequestTable
      :requests="requests"
      :selected-id="selectedRequest?.request_id ?? null"
      :page="page"
      :page-size="pageSize"
      @select="handleSelect"
      @update:page="onPageChange"
    />

    <!-- Modal -->
    <div
      v-if="showModal && selectedRequest"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      @click.self="closeModal"
    >
      <div class="max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-lg bg-gray-900 border border-gray-700 shadow-xl">
        <div class="sticky top-0 z-10 flex items-center justify-between border-b border-gray-700 bg-gray-800 px-4 py-3">
          <h2 class="text-base font-semibold text-gray-100">Request Detail</h2>
          <button
            class="rounded-md px-3 py-1 text-sm bg-gray-700 text-gray-300 hover:bg-gray-600"
            @click="closeModal"
          >
            Close
          </button>
        </div>
        <div class="space-y-4 p-4">
          <RequestDetail :request="selectedRequest" />

          <!-- Job logs, loaded with the detail when the request started a job -->
          <section v-if="logsJobId" class="job-logs-section space-y-2">
            <div class="flex items-center justify-between gap-4">
              <h3 class="flex items-center gap-2 text-sm font-semibold text-gray-100">
                Logs
                <span v-if="live" class="live-badge rounded bg-green-900 px-2 py-0.5 text-xs text-green-300">● Live</span>
              </h3>
              <button
                class="rounded-md px-3 py-1 text-sm bg-gray-700 text-gray-300 hover:bg-gray-600"
                :disabled="jobLogsLoading"
                @click="store.fetchJobLogs(logsJobId)"
              >
                {{ jobLogsLoading ? 'Loading...' : 'Refresh logs' }}
              </button>
            </div>
            <JobLogs :logs="displayedLogs" :loading="jobLogsLoading" :error="jobLogsError" />
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useTrackingStore } from '@/stores/useTrackingStore'
import type { JobLogs as JobLogsData, RequestLog } from '@/services/api'
import RequestTable from './components/RequestTable.vue'
import RequestDetail from './components/RequestDetail.vue'
import JobLogs from './components/JobLogs.vue'
import { useWebSocketLogger } from '@/composables/useWebSocketLogger'

const store = useTrackingStore()
const selectedRequest = ref<RequestLog | null>(null)
const showModal = ref(false)
const page = ref(0)
const pageSize = 10
const endpointFilter = ref('')

// storeToRefs keeps the view in sync when the store replaces these values.
const { requests, error, loading, jobLogs, jobLogsLoading, jobLogsError } = storeToRefs(store)
const logsJobId = ref<string | null>(null)

// Loaded on mount and on Refresh (or Enter in the filter) only: no polling.
// The table pages through these MAX_REQUESTS client-side, 10 per page.
const MAX_REQUESTS = 50

onMounted(() => {
  refresh()
})

function refresh() {
  page.value = 0
  store.fetchRequests(MAX_REQUESTS, endpointFilter.value || undefined)
}

function onPageChange(p: number) {
  page.value = p
}

async function handleSelect(requestId: string) {
  await store.fetchRequest(requestId)
  selectedRequest.value = store.selected
  showModal.value = true
  const jobId = selectedRequest.value?.job_id
  if (jobId) openLogs(jobId)
}

function closeModal() {
  closeLogs()
  showModal.value = false
}

// Job logs: loaded over HTTP with the detail (and on Refresh). A pending or running job is
// then followed live over the log WebSocket until it ends; the final state is reloaded once.
const ws = useWebSocketLogger()
const live = ref(false)

async function openLogs(jobId: string) {
  stopLive()
  logsJobId.value = jobId
  jobLogs.value = null  // never show the previous job's logs while loading
  await store.fetchJobLogs(jobId)
  const status = jobLogs.value?.status
  if (logsJobId.value === jobId && (status === 'pending' || status === 'running')) {
    live.value = true
    ws.connect(jobId)
  }
}

function stopLive() {
  live.value = false
  ws.disconnect()
  ws.clearLogs()
}

function closeLogs() {
  stopLive()
  logsJobId.value = null
}

watch(ws.isCompleted, (done) => {
  if (done && live.value && logsJobId.value) {
    const jobId = logsJobId.value
    stopLive()
    store.fetchJobLogs(jobId)
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