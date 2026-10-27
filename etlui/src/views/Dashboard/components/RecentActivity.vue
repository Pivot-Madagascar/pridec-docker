<template>
  <!-- Always shown (the Dashboard fixes it on the left); <details>: the whole panel folds natively. -->
  <details open class="activity-section">
    <summary class="activity-summary">Recent Activity</summary>
    <p v-if="activityLog.length === 0" class="activity-empty">No activity yet: launches and decisions show here.</p>
    <!-- shadcn Trace: one line per entry, the icon and colour of its status (success, error: Trace's own red);
         unfolding shows the message and, for a job, its request and logs. -->
    <Trace v-if="activityLog.length" class="px-4 pb-3">
      <TraceCollapsible v-for="entry in activityLog" :key="entry.id" data-test="activity-entry">
        <TraceCollapsibleTrigger>
          <TraceLine :status="entry.success ? undefined : 'error'">
            <TraceIcon :class="entry.success ? 'text-success' : 'text-destructive'">
              <CircleCheck v-if="entry.success" data-test="status-success" />
              <CircleX v-else data-test="status-error" />
            </TraceIcon>
            <TraceTitle>{{ entry.action }}</TraceTitle>
            <TraceDescription>{{ entry.time }}</TraceDescription>
          </TraceLine>
        </TraceCollapsibleTrigger>
        <TraceCollapsibleContent class="text-xs">
          <p>{{ entry.message }}</p>
          <!-- Only activities that started a job have something to show: their request and logs -->
          <Button v-if="entry.jobId" variant="link" size="xs" class="px-0" data-test="detail-btn" @click="openDetail(entry)">
            Request and logs
          </Button>
        </TraceCollapsibleContent>
      </TraceCollapsible>
    </Trace>

    <!-- Same dialog as the tracking page: the tracked request (found by its X-Request-ID), then the job logs.
         Not tracked (TRACKED_ENDPOINTS) or not found: the logs still load from the job_id. -->
    <RequestDialog :open="!!logsJobId" :request="request" :job-id="logsJobId" :error="error" @close="logsJobId = null" />
  </details>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import type { ActivityEntry } from '@/composables/useActivityLog'
import type { RequestLog } from '@/services/api'
import { useTrackingStore } from '@/stores/useTrackingStore'
import RequestDialog from '@/views/TrackerView/components/RequestDialog.vue'
import { Button } from '@/components/ui/button'
import {
  Trace, TraceCollapsible, TraceCollapsibleContent, TraceCollapsibleTrigger, TraceDescription, TraceIcon, TraceLine, TraceTitle
} from '@/components/ui/trace'
import { CircleCheck, CircleX } from '@lucide/vue'

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
