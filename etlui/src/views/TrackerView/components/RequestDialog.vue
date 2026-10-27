<template>
  <!-- The request, then its job logs: Tracking, Recent Activity and the Journal. Content only while open: closing stops the live logs. -->
  <BaseDialog :open="open" backdrop-close class="request-dialog" @dismiss="emit('close')">
    <template v-if="open">
      <div class="sticky top-0 z-10 flex items-center justify-between border-b border-gray-700 bg-gray-800 px-4 py-3">
        <h2 class="text-base font-semibold text-gray-100">{{ title ?? 'Request Detail' }}</h2>
        <Button variant="secondary" size="sm" @click="emit('close')">Close</Button>
      </div>
      <div class="space-y-4 p-4">
        <RequestDetail v-if="request" :request="request" />
        <p v-else-if="error" class="text-sm text-red-300">{{ error }}</p>
        <JobLogsPanel v-if="jobId" :job-id="jobId" />
      </div>
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
import type { RequestLog } from '@/services/api'
import BaseDialog from '@/views/Dashboard/components/BaseDialog.vue'
import RequestDetail from './RequestDetail.vue'
import JobLogsPanel from './JobLogsPanel.vue'
import { Button } from '@/components/ui/button'

defineProps<{
  open: boolean
  request?: RequestLog | null
  jobId?: string | null
  error?: string
  title?: string
}>()

const emit = defineEmits<{ close: [] }>()
</script>

<style scoped>
.request-dialog {
  width: 100%;
  max-width: 64rem;
  max-height: 90vh;
  padding: 0;
  overflow-y: auto;
  background: #111827;
  border-color: #374151;
  border-radius: 0.5rem;
}
</style>
