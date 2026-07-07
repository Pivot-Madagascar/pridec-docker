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
          <button
            v-if="entry.jobId"
            class="text-xs text-blue-400 hover:text-blue-300"
            @click="viewLogs(entry.jobId)"
          >
            Voir Logs
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const props = defineProps<{
  activityLog: Array<{
    id: number
    action: string
    message: string
    time: string
    success: boolean
    jobId?: string
  }>
}>()

const router = useRouter()

function viewLogs(jobId: string) {
  router.push({ path: '/logs', query: { jobId } })
}
</script>