<template>
  <div>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="rounded-lg bg-gray-900 border border-gray-700 p-4">
        <p class="text-xs text-gray-500">Request ID</p>
        <p class="mt-1 font-mono text-sm text-gray-200 break-all">
          {{ request.request_id }}
        </p>
      </div>
      <div class="rounded-lg bg-gray-900 border border-gray-700 p-4">
        <p class="text-xs text-gray-500">Method</p>
        <p class="mt-1 text-sm text-gray-200">{{ request.method }}</p>
      </div>
      <div class="rounded-lg bg-gray-900 border border-gray-700 p-4">
        <p class="text-xs text-gray-500">Status</p>
        <p class="mt-1 text-sm" :class="statusColor(request.status_code)">
          {{ request.status_code }}
        </p>
      </div>
      <div class="rounded-lg bg-gray-900 border border-gray-700 p-4">
        <p class="text-xs text-gray-500">URL</p>
        <p class="mt-1 font-mono text-xs text-gray-300 break-all">
          {{ request.url }}
        </p>
      </div>
      <div class="rounded-lg bg-gray-900 border border-gray-700 p-4">
        <p class="text-xs text-gray-500">Duration</p>
        <p class="mt-1 text-sm text-gray-200">{{ request.duration_ms.toFixed(2) }} ms</p>
      </div>
      <div class="rounded-lg bg-gray-900 border border-gray-700 p-4">
        <p class="text-xs text-gray-500">Client Host</p>
        <p class="mt-1 text-sm text-gray-200">
          {{ request.client_host ?? '-' }}
        </p>
      </div>
    </div>

    <div v-if="request.error" class="rounded-lg border border-red-900 bg-red-950 p-4 mt-4">
      <p class="text-xs text-red-400">Error</p>
      <p class="mt-1 text-sm text-red-200">{{ request.error }}</p>
    </div>

    <div
      v-if="request.services && request.services.length"
      class="rounded-lg border border-gray-700 bg-gray-900 mt-6"
    >
      <div class="border-b border-gray-700 px-4 py-2">
        <h3 class="text-sm font-semibold text-gray-200">Services Called</h3>
      </div>
      <table class="min-w-full text-sm">
        <thead class="bg-gray-800 text-gray-300">
          <tr>
            <th class="px-4 py-2 text-left">Service</th>
            <th class="px-4 py-2 text-left">Method</th>
            <th class="px-4 py-2 text-left">URL</th>
            <th class="px-4 py-2 text-left">Status</th>
            <th class="px-4 py-2 text-right">Duration (ms)</th>
            <th class="px-4 py-2 text-left">Error</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-700">
          <tr
            v-for="svc in request.services"
            :key="`${svc.service}-${svc.url}-${svc.method}`"
          >
            <td class="px-4 py-2 text-gray-200">{{ svc.service }}</td>
            <td class="px-4 py-2 text-gray-300">{{ svc.method }}</td>
            <td class="px-4 py-2 font-mono text-xs text-gray-400 break-all">
              {{ svc.url }}
            </td>
            <td class="px-4 py-2">
              <span
                class="inline-block rounded px-2 py-0.5 text-xs font-semibold"
                :class="statusColor(svc.status_code ?? 0)"
              >
                {{ svc.status_code ?? '-' }}
              </span>
            </td>
            <td class="px-4 py-2 text-right font-mono text-xs text-gray-300">
              {{ svc.duration_ms != null ? svc.duration_ms.toFixed(2) : '-' }}
            </td>
            <td class="px-4 py-2 text-xs text-red-400">
              {{ svc.error ?? '-' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { RequestLog } from '@/services/api'

defineProps<{
  request: RequestLog | null
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
