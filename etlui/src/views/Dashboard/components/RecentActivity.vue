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
          <Button v-if="entry.jobId" variant="link" size="xs" data-test="detail-btn" @click="openDetail(entry)">Detail</Button>
        </div>
      </div>
    </div>

    <!-- Same dialog as the tracking page: the tracked request (found by its X-Request-ID), then the job logs.
         Not tracked (TRACKED_ENDPOINTS) or not found: the logs still load from the job_id. -->
    <RequestDialog :open="!!logsJobId" :request="request" :job-id="logsJobId" :error="error" @close="logsJobId = null" />
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import type { ActivityEntry } from '@/composables/useActivityLog'
import type { RequestLog } from '@/services/api'
import { useTrackingStore } from '@/stores/useTrackingStore'
import RequestDialog from '@/views/TrackerView/components/RequestDialog.vue'
import { Button } from '@/components/ui/button'

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
