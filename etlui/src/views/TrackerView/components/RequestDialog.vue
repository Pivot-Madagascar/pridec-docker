<template>
  <!-- The request, then its job logs: Tracking, Recent Activity and the Journal. Content only while open: closing stops the live logs. -->
  <Dialog :open="open" @update:open="!$event && emit('close')">
    <DialogContent class="flex max-h-[90vh] flex-col gap-0 p-0 sm:max-w-5xl" :aria-describedby="undefined">
      <div class="border-b bg-card py-4 pr-14 pl-4">
        <DialogTitle class="text-base">{{ title ?? 'Request Detail' }}</DialogTitle>
      </div>
      <div class="min-h-0 space-y-4 overflow-y-auto p-4">
        <RequestDetail v-if="request" :request="request" />
        <p v-else-if="error" class="text-sm text-destructive">{{ error }}</p>
        <JobLogsPanel v-if="jobId" :job-id="jobId" />
      </div>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import type { RequestLog } from '@/services/api'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import RequestDetail from './RequestDetail.vue'
import JobLogsPanel from './JobLogsPanel.vue'

defineProps<{
  open: boolean
  request?: RequestLog | null
  jobId?: string | null
  error?: string
  title?: string
}>()

const emit = defineEmits<{ close: [] }>()
</script>
