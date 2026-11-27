<template>
  <!-- Always shown, a shadcn Card (the Forecast page's right column, like the reference's "Recent Jobs"). -->
  <Card class="gap-3 py-4">
    <CardHeader class="px-4">
      <CardTitle>Recent Activity</CardTitle>
      <CardAction>
        <Button variant="link" size="sm" class="h-auto p-0" as-child><RouterLink to="/tracking">View all</RouterLink></Button>
      </CardAction>
    </CardHeader>
    <p v-if="error" class="px-4 text-sm text-destructive" data-test="activity-error">{{ error }}</p>
    <p v-if="activityLog.length === 0" class="px-4 text-sm text-muted-foreground">
      No activity yet in this pass: its last {{ RECENT }} requests show here (a running job, once it ends).
    </p>
    <!-- shadcn Trace: one line per entry, the icon and colour of its status (success, error: Trace's own red);
         unfolding shows the message and, for a job, its request and logs. -->
    <Trace v-if="activityLog.length" class="px-4">
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
          <!-- The tracked request (while etlhub keeps it) and, for a job, its logs -->
          <Button v-if="entry.request || entry.jobId" variant="link" size="xs" class="px-0" data-test="detail-btn" @click="openDetail(entry)">
            {{ entry.jobId ? 'Request and logs' : 'Request' }}
          </Button>
        </TraceCollapsibleContent>
      </TraceCollapsible>
    </Trace>

    <!-- Same dialog as the tracking page: the request the journal joined to the event, then the job logs.
         No longer kept by etlhub: the logs still load from the job_id. -->
    <RequestDialog :open="!!shown" :request="shown?.request" :job-id="shown?.jobId" @close="shown = null" />
  </Card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RECENT, type ActivityEntry } from '@/composables/usePassActivity'
import RequestDialog from '@/views/TrackerView/components/RequestDialog.vue'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Trace, TraceCollapsible, TraceCollapsibleContent, TraceCollapsibleTrigger, TraceDescription, TraceIcon, TraceLine, TraceTitle
} from '@/components/ui/trace'
import { CircleCheck, CircleX } from '@lucide/vue'

defineProps<{
  activityLog: ActivityEntry[] // the pass's last requests, from its journal (usePassActivity)
  error?: string
}>()

const shown = ref<ActivityEntry | null>(null)
const openDetail = (entry: ActivityEntry) => (shown.value = entry)
</script>
