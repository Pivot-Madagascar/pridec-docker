<template>
  <!-- No side panel: SideLayout keeps the page where Forecast and Journal have theirs. -->
  <SideLayout class="space-y-6">
    <div class="flex items-center justify-between gap-4">
      <h1 class="text-2xl font-bold text-foreground">Request Tracking</h1>
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

    <div v-if="error" class="rounded-lg border border-destructive/40 bg-destructive/15 p-3 text-sm text-destructive">
      {{ error }}
    </div>

    <div class="space-y-2">
      <TablePager
        :sizes="PAGE_SIZES"
        v-model:page-size="settings.pageSize"
        v-model:newest-first="settings.newestFirst"
        v-model:page="page"
        :total-pages="totalPages"
      />
      <RequestTable :requests="rows" :selected-id="selected?.request_id ?? null" @select="handleSelect" />
    </div>

    <RequestDialog :open="showModal && !!selected" :request="selected" :job-id="selected?.job_id" @close="showModal = false" />
  </SideLayout>
</template>

<script setup lang="ts">
import SideLayout from '@/components/SideLayout.vue'
import { onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useTrackingStore } from '@/stores/useTrackingStore'
import RequestTable from './components/RequestTable.vue'
import RequestDialog from './components/RequestDialog.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import TablePager from '@/components/TablePager.vue'
import { useTablePaging } from '@/composables/useTablePaging'

const store = useTrackingStore()
const showModal = ref(false)
const endpointFilter = ref('')

// storeToRefs keeps the view in sync when the store replaces these values.
const { requests, error, loading, selected } = storeToRefs(store)

// Loaded on mount and on Refresh (or Enter in the filter) only: no polling.
// The table pages through these MAX_REQUESTS client-side; etlhub sends them newest first.
// ponytail: client-side pages over the last 500; server-side paging (offset) if older requests are needed.
const MAX_REQUESTS = 500
const PAGE_SIZES = [10, 25, 50, 100]
const { settings, page, rows, totalPages } = useTablePaging('tracking', requests, { sizes: PAGE_SIZES, defaultSize: 10, sourceNewestFirst: true })

onMounted(() => {
  refresh()
})

function refresh() {
  store.fetchRequests(MAX_REQUESTS, endpointFilter.value || undefined)
}

async function handleSelect(requestId: string) {
  await store.fetchRequest(requestId)
  showModal.value = true
}
</script>