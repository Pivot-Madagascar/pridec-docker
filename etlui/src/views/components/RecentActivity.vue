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
        <span class="activity-time">{{ entry.time }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
const props = defineProps<{
  activityLog: Array<{
    id: number
    action: string
    message: string
    time: string
    success: boolean
  }>
}>()
</script>