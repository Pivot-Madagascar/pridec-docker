<template>
  <!-- The content of a toast: a message, or a job's (followJob) every step reached so far, the last one live. -->
  <div class="job-toast min-w-56 text-left">
    <div class="flex items-start gap-2">
      <p class="flex-1 text-sm font-semibold text-popover-foreground">{{ label }}</p>
      <!-- Pinned: the toast no longer closes on its own; × closes it at once. -->
      <Button variant="ghost" size="icon-xs" data-test="toast-pin" :aria-pressed="pinned"
        :aria-label="pinned ? 'Unpin' : 'Pin'" :title="pinned ? 'Unpin' : 'Pin'"
        :class="{ 'text-primary': pinned }" @click="emit('pin')">
        <PinOff v-if="pinned" aria-hidden="true" />
        <Pin v-else aria-hidden="true" />
      </Button>
      <Button variant="ghost" size="icon-xs" data-test="toast-close" aria-label="Close" title="Close" @click="emit('close')">
        <X aria-hidden="true" />
      </Button>
    </div>
    <ol v-if="steps.length" class="mt-1.5 space-y-1.5 border-l border-border pl-3">
      <li v-for="(step, index) in steps" :key="step.key" class="relative text-xs leading-snug">
        <span
          class="absolute -left-[17px] top-1 h-2 w-2 rounded-full"
          :class="[DOT[step.key], { 'animate-pulse': index === steps.length - 1 && !ENDS.has(step.key) }]"
        />
        <span class="font-medium" :class="TEXT[step.key]">{{ TITLE[step.key] }}</span>
        <span class="text-muted-foreground"> · {{ step.at }}</span>
        <span v-if="step.detail" class="block break-words text-muted-foreground">
          {{ step.detail }}<template v-if="step.key === 'accepted' && jobId"> · <RouterLink
            :to="{ name: 'ETLLogs', query: { jobId } }" class="font-mono text-primary underline-offset-2 hover:underline"
            data-test="toast-job-link" title="Follow its logs live">{{ jobId }}</RouterLink></template>
        </span>
      </li>
    </ol>
  </div>
</template>

<script setup lang="ts">
import { Pin, PinOff, X } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import type { JobStep } from '@/composables/useNotification'

// jobId: a job's toast; its id links to the Logs page, which follows it at once (?jobId=).
withDefaults(defineProps<{ label: string; steps?: JobStep[]; pinned?: boolean; jobId?: string }>(), { steps: () => [], pinned: false })
const emit = defineEmits<{ pin: []; close: [] }>()

const ENDS = new Set(['success', 'error'])
const TITLE: Record<JobStep['key'], string> = { accepted: 'Accepted', running: 'Running', success: 'Completed', error: 'Failed' }
// The app's tokens (base.css), so the toast follows its light / dark theme.
const DOT: Record<JobStep['key'], string> = {
  accepted: 'bg-primary', running: 'bg-warning', success: 'bg-success', error: 'bg-destructive',
}
const TEXT: Record<JobStep['key'], string> = {
  accepted: 'text-primary', running: 'text-warning', success: 'text-success', error: 'text-destructive',
}
</script>

<style>
/* The toaster's own icon (spinner, green tick, red cross) just before a job toast: larger, a bit more to the left.
   scale() keeps the library's 20px box, so the margins make the room: 2px from the edge, 14px before the steps. */
[data-toasts] .indicator-wrapper:has(+ .job-toast) {
  transform: scale(1.5);
  margin: 0 14px 0 2px;
}
</style>
