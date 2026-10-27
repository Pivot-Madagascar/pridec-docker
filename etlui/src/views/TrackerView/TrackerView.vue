<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between gap-4">
      <h1 class="text-2xl font-bold text-gray-100">Request Tracking</h1>
      <div class="flex items-center gap-2">
        <Input
          v-model="endpointFilter"
          type="text"
          placeholder="Filter by endpoint (e.g. /import_gee)"
          @keyup.enter="refresh"
          aria-label="Filter by endpoint"
          class="w-64"
        />
        <Button variant="secondary" @click="refresh" :disabled="loading">
          {{ loading ? 'Loading...' : 'Refresh' }}
        </Button>
      </div>
    </div>

    <div v-if="error" class="rounded-lg border border-red-900 bg-red-950 p-3 text-sm text-red-300">
      {{ error }}
    </div>

    <RequestTable
      :requests="requests"
      :selected-id="selected?.request_id ?? null"
      v-model:page="page"
      @select="handleSelect"
    />

    <RequestDialog :open="showModal && !!selected" :request="selected" :job-id="selected?.job_id" @close="showModal = false" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useTrackingStore } from '@/stores/useTrackingStore'
import RequestTable from './components/RequestTable.vue'
import RequestDialog from './components/RequestDialog.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const store = useTrackingStore()
const showModal = ref(false)
const page = ref(0)
const endpointFilter = ref('')

// storeToRefs keeps the view in sync when the store replaces these values.
const { requests, error, loading, selected } = storeToRefs(store)

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

async function handleSelect(requestId: string) {
  await store.fetchRequest(requestId)
  showModal.value = true
}
</script>