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
          <!-- Only activities that started a job have something to show: their logs -->
          <button
            v-if="entry.jobId"
            class="detail-btn text-xs text-blue-400 hover:text-blue-300"
            @click="logsJobId = entry.jobId"
          >
            Detail
          </button>
        </div>
      </div>
    </div>

    <!-- Same modal as the tracking page, logs only: an activity has no request record -->
    <div
      v-if="logsJobId"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      @click.self="logsJobId = null"
    >
      <div class="max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-lg bg-gray-900 border border-gray-700 shadow-xl">
        <div class="sticky top-0 z-10 flex items-center justify-between border-b border-gray-700 bg-gray-800 px-4 py-3">
          <h2 class="text-base font-semibold text-gray-100">
            Job Detail <span class="font-mono text-xs text-gray-400">{{ logsJobId }}</span>
          </h2>
          <button
            class="rounded-md px-3 py-1 text-sm bg-gray-700 text-gray-300 hover:bg-gray-600"
            @click="logsJobId = null"
          >
            Close
          </button>
        </div>
        <div class="p-4">
          <JobLogsPanel :job-id="logsJobId" />
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { ActivityEntry } from '@/composables/useActivityLog'
import JobLogsPanel from '@/views/TrackerView/components/JobLogsPanel.vue'

defineProps<{
  activityLog: ActivityEntry[]
}>()

const logsJobId = ref<string | null>(null)
</script>
