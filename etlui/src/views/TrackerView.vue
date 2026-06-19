<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-gray-100">Request Tracking</h1>
      <button
        class="rounded-md px-4 py-1.5 text-sm bg-gray-800 text-gray-300 hover:bg-gray-700"
        @click="refresh"
        :disabled="loading"
      >
        {{ loading ? 'Loading...' : 'Refresh' }}
      </button>
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
      v-if="showModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      @click.self="closeModal"
    >
      <div class="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-lg bg-gray-900 border border-gray-700 shadow-xl">
        <div class="sticky top-0 z-10 flex items-center justify-between border-b border-gray-700 bg-gray-800 px-4 py-3">
          <h2 class="text-base font-semibold text-gray-100">Request Detail</h2>
          <button
            class="rounded-md px-3 py-1 text-sm bg-gray-700 text-gray-300 hover:bg-gray-600"
            @click="closeModal"
          >
            Close
          </button>
        </div>
        <div class="p-4">
          <RequestDetail :request="selectedRequest" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useTrackingStore } from '@/stores/useTrackingStore'
import RequestTable from '@/views/components/RequestTable.vue'
import RequestDetail from '@/views/components/RequestDetail.vue'

const store = useTrackingStore()
const selectedRequest = ref<import('@/services/api').RequestLog | null>(null)
const showModal = ref(false)
const page = ref(0)
const pageSize = 10

const requests = store.requests
const error = store.error
const loading = store.loading

onMounted(() => {
  refresh()
})

onUnmounted(() => {
  store.stopPolling()
})

function refresh() {
  store.stopPolling()
  const limit = (page.value + 1) * pageSize
  store.fetchRequests(limit)
}

function onPageChange(p: number) {
  page.value = p
  const limit = (page.value + 1) * pageSize
  store.fetchRequests(limit)
}

async function handleSelect(requestId: string) {
  await store.fetchRequest(requestId)
  selectedRequest.value = store.selected
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}
</script>
