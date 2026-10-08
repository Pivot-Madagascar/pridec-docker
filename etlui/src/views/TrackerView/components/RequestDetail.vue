<template>
  <table class="w-full table-fixed text-sm">
    <thead class="text-left text-xs text-gray-500">
      <tr>
        <th class="w-20 px-3 py-2 font-normal">Method</th>
        <th class="w-20 px-3 py-2 font-normal">Status</th>
        <th class="px-3 py-2 font-normal">URL</th>
        <th class="w-28 px-3 py-2 font-normal">Duration</th>
        <th class="w-48 px-3 py-2 font-normal">Job ID</th>
      </tr>
    </thead>
    <tbody>
      <tr class="border-t border-gray-700 text-gray-200">
        <td class="px-3 py-2">{{ request.method }}</td>
        <td class="px-3 py-2" :class="statusColor(request.status_code)">{{ request.status_code }}</td>
        <td class="px-3 py-2 font-mono text-xs break-all">{{ request.url }}</td>
        <td class="px-3 py-2">{{ request.duration_ms.toFixed(2) }} ms</td>
        <td class="px-3 py-2 font-mono text-xs break-all">{{ request.job_id ?? '-' }}</td>
      </tr>
    </tbody>
  </table>
</template>

<script setup lang="ts">
import type { RequestLog } from '@/services/api'

defineProps<{
  request: RequestLog
}>()

function statusColor(statusCode: number) {
  if (statusCode >= 200 && statusCode < 300) {
    return 'text-green-400'
  }
  if (statusCode >= 400 && statusCode < 500) {
    return 'text-yellow-400'
  }
  if (statusCode >= 500) {
    return 'text-red-400'
  }
  return 'text-gray-300'
}
</script>
