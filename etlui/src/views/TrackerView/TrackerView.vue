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
          <JobLogsPanel v-if="logsJobId" :job-id="logsJobId" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useTrackingStore } from '@/stores/useTrackingStore'
import type { RequestLog } from '@/services/api'
import RequestTable from './components/RequestTable.vue'
import RequestDetail from './components/RequestDetail.vue'
import JobLogsPanel from './components/JobLogsPanel.vue'

const store = useTrackingStore()
const selectedRequest = ref<RequestLog | null>(null)
const showModal = ref(false)
const page = ref(0)
const pageSize = 10
const endpointFilter = ref('')

// storeToRefs keeps the view in sync when the store replaces these values.
const { requests, error, loading } = storeToRefs(store)
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
  logsJobId.value = selectedRequest.value?.job_id ?? null
}

function closeModal() {
  logsJobId.value = null
  showModal.value = false
}
</script>