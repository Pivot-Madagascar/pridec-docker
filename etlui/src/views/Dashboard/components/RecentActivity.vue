<template>
  <section v-if="activityLog.length > 0" class="activity-section">
    <h2 class="section-header">Recent Activity</h2>
    <div class="activity-divide">
      <div v-for="entry in activityLog" :key="entry.id" class="activity-item">
        <div class="flex-row-center space-x-3">
          <div class="activity-icon" :class="entry.success ? 'activity-icon-success' : 'activity-icon-error'"></div>
          <div>
            <p class="activity-action">{{ entry.action }}</p>
            <p class="activity-message">{{ entry.message }}</p>
          </div>
        </div>
        <div class="flex-row-center space-x-2">
          <span class="activity-time">{{ entry.time }}</span>
          <!-- Only activities that started a job have something to show: their request and logs -->
          <button
            v-if="entry.jobId"
            class="detail-btn text-xs text-blue-400 hover:text-blue-300"
            @click="openDetail(entry)"
          >
            Detail
          </button>
        </div>
      </div>
    </div>

    <!-- Same modal as the tracking page: the tracked request (found by its X-Request-ID), then the job logs -->
    <div
      v-if="logsJobId"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      @click.self="logsJobId = null"
    >
      <div class="max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-lg bg-gray-900 border border-gray-700 shadow-xl">
        <div class="sticky top-0 z-10 flex items-center justify-between border-b border-gray-700 bg-gray-800 px-4 py-3">
          <h2 class="text-base font-semibold text-gray-100">Request Detail</h2>
          <button
            class="rounded-md px-3 py-1 text-sm bg-gray-700 text-gray-300 hover:bg-gray-600"
            @click="logsJobId = null"
          >
            Close
          </button>
        </div>
        <div class="space-y-4 p-4">
          <RequestDetail v-if="request" :request="request" />
          <!-- Not tracked (TRACKED_ENDPOINTS) or not found: the logs still load from the job_id -->
          <p v-else-if="error" class="text-sm text-red-300">{{ error }}</p>
          <JobLogsPanel :job-id="logsJobId" />
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import type { ActivityEntry } from '@/composables/useActivityLog'
import type { RequestLog } from '@/services/api'
import { useTrackingStore } from '@/stores/useTrackingStore'
import RequestDetail from '@/views/TrackerView/components/RequestDetail.vue'
import JobLogsPanel from '@/views/TrackerView/components/JobLogsPanel.vue'

defineProps<{
  activityLog: ActivityEntry[]
}>()

const store = useTrackingStore()
const { error } = storeToRefs(store)
const logsJobId = ref<string | null>(null)
const request = ref<RequestLog | null>(null)

// Same as TrackerView's handleSelect, from the activity's requestId instead of a table row.
async function openDetail(entry: ActivityEntry) {
  request.value = null
  logsJobId.value = entry.jobId ?? null
  if (!entry.requestId) return
  await store.fetchRequest(entry.requestId)
  // fetchRequest keeps the previous selection on error: only show this activity's request
  request.value = store.selected?.request_id === entry.requestId ? store.selected : null
}
</script>
