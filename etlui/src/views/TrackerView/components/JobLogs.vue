<template>
  <div class="space-y-4">
    <div v-if="error" class="rounded-lg border border-red-900 bg-red-950 p-3 text-sm text-red-300">
      {{ error }}
    </div>

    <template v-else-if="logs">
      <div class="flex flex-wrap items-center gap-3 text-sm">
        <span class="text-gray-500">Status</span>
        <span class="rounded px-2 py-0.5 text-xs font-semibold" :class="statusColor(logs.status)">
          {{ logs.status ?? 'unknown (record expired)' }}
        </span>
        <span v-if="logs.message" class="text-gray-300">{{ logs.message }}</span>
      </div>
      <pre class="max-h-[60vh] overflow-auto whitespace-pre-wrap rounded-lg border border-gray-700 bg-black/40 p-3 font-mono text-xs text-gray-200">{{ logs.logs || 'No logs yet.' }}</pre>
    </template>

    <p v-else-if="loading" class="text-sm text-gray-400">Loading logs...</p>
  </div>
</template>

<script setup lang="ts">
import type { JobLogs } from '@/services/api'

defineProps<{
  logs: JobLogs | null
  loading: boolean
  error: string
}>()

function statusColor(status: string | null) {
  if (status === 'success') return 'bg-green-900 text-green-300'
  if (status === 'error') return 'bg-red-900 text-red-300'
  if (status === 'running' || status === 'pending') return 'bg-blue-900 text-blue-300'
  return 'bg-gray-700 text-gray-300'
}
</script>
