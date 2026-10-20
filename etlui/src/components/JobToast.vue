<template>
  <!-- The content of a job's toast (followJob): every step reached so far, the last one live. -->
  <div class="job-toast min-w-56 text-left">
    <p class="text-sm font-semibold text-gray-900">{{ label }}</p>
    <ol class="mt-1.5 space-y-1.5 border-l border-gray-200 pl-3">
      <li v-for="(step, index) in steps" :key="step.key" class="relative text-xs leading-snug">
        <span
          class="absolute -left-[17px] top-1 h-2 w-2 rounded-full"
          :class="[DOT[step.key], { 'animate-pulse': index === steps.length - 1 && !ENDS.has(step.key) }]"
        />
        <span class="font-medium" :class="TEXT[step.key]">{{ TITLE[step.key] }}</span>
        <span class="text-gray-400"> · {{ step.at }}</span>
        <span v-if="step.detail" class="block break-words text-gray-600">{{ step.detail }}</span>
      </li>
    </ol>
  </div>
</template>

<script setup lang="ts">
import type { JobStep } from '@/composables/useNotification'

defineProps<{ label: string; steps: JobStep[] }>()

const ENDS = new Set(['success', 'error'])
const TITLE: Record<JobStep['key'], string> = { accepted: 'Accepted', running: 'Running', success: 'Completed', error: 'Failed' }
const DOT: Record<JobStep['key'], string> = {
  accepted: 'bg-blue-500', running: 'bg-amber-500', success: 'bg-green-500', error: 'bg-red-500',
}
const TEXT: Record<JobStep['key'], string> = {
  accepted: 'text-blue-700', running: 'text-amber-700', success: 'text-green-700', error: 'text-red-700',
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
