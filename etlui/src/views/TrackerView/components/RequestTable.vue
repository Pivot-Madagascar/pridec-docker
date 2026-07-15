<template>
  <div class="overflow-hidden rounded-lg border border-gray-700">
    <table class="min-w-full text-sm">
      <thead class="bg-gray-800 text-gray-200">
        <tr>
          <th class="px-4 py-2 text-left">Request ID</th>
          <th class="px-4 py-2 text-left">Time</th>
          <th class="px-4 py-2 text-left">Method</th>
          <th class="px-4 py-2 text-left">Status</th>
          <th class="px-4 py-2 text-right">Duration (ms)</th>
          <th class="px-4 py-2"></th>
        </tr>
      </thead>
      <tbody class="divide-y divide-gray-700 bg-gray-900">
        <tr
          v-for="req in paginated"
          :key="req.request_id"
          :class="{
            'bg-gray-800': selectedId === req.request_id,
            'hover:bg-gray-750': selectedId !== req.request_id,
          }"
          class="cursor-pointer"
          @click="$emit('select', req.request_id)"
        >
          <td class="px-4 py-2 font-mono text-xs text-gray-300">
            {{ shortRequestId(req.request_id) }}
          </td>
          <td class="px-4 py-2 text-xs text-gray-400">
            {{ formatTime(req.duration_ms) }}
          </td>
          <td class="px-4 py-2">
            <span
              class="inline-block rounded px-2 py-0.5 text-xs font-semibold"
              :class="methodColor(req.method)"
            >
              {{ req.method }}
            </span>
          </td>
          <td class="px-4 py-2">
            <span
              class="inline-block rounded px-2 py-0.5 text-xs font-semibold"
              :class="statusColor(req.status_code)"
            >
              {{ req.status_code }}
            </span>
          </td>
          <td class="px-4 py-2 text-right font-mono text-xs text-gray-300">
            {{ req.duration_ms.toFixed(2) }}
          </td>
          <td class="px-4 py-2 text-right">
            <button
              class="text-xs text-blue-400 hover:text-blue-300"
              @click.stop="$emit('select', req.request_id)"
            >
              Detail
            </button>
          </td>
        </tr>
        <tr v-if="!requests.length">
          <td colspan="6" class="px-4 py-6 text-center text-gray-500">
            No requests recorded yet.
          </td>
        </tr>
      </tbody>
    </table>

    <div class="flex items-center justify-end border-t border-gray-700 bg-gray-900 px-4 py-2 space-x-2">
      <button
        class="rounded px-2 py-1 text-xs bg-gray-800 text-gray-300 hover:bg-gray-700 disabled:opacity-50"
        :disabled="page <= 0"
        @click="$emit('update:page', page - 1)"
      >
        Prev
      </button>
      <span class="text-xs text-gray-400">Page {{ page + 1 }} / {{ totalPages || 1 }}</span>
      <button
        class="rounded px-2 py-1 text-xs bg-gray-800 text-gray-300 hover:bg-gray-700 disabled:opacity-50"
        :disabled="page + 1 >= totalPages"
        @click="$emit('update:page', page + 1)"
      >
        Next
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RequestLog } from '@/services/api'

const props = defineProps<{
  requests: RequestLog[]
  selectedId?: string | null
  page?: number
  pageSize?: number
}>()

defineEmits<{
  (e: 'select', requestId: string): void
  (e: 'update:page', page: number): void
}>()

const page = computed({
  get: () => props.page ?? 0,
  set: (v: number) => emit('update:page', v),
})
const pageSize = props.pageSize ?? 10

const paginated = computed(() => {
  const start = page.value * pageSize
  return props.requests.slice(start, start + pageSize)
})

const totalPages = computed(() => Math.max(1, Math.ceil(props.requests.length / pageSize)))

function shortRequestId(requestId: string) {
  return requestId.length > 12 ? requestId.slice(0, 12) + '...' : requestId
}

function formatTime(durationMs: number) {
  return new Date().toLocaleTimeString()
}

function methodColor(method: string) {
  switch (method) {
    case 'GET':
      return 'bg-green-900 text-green-300'
    case 'POST':
      return 'bg-blue-900 text-blue-300'
    case 'PUT':
      return 'bg-yellow-900 text-yellow-300'
    case 'DELETE':
      return 'bg-red-900 text-red-300'
    default:
      return 'bg-gray-700 text-gray-300'
  }
}

function statusColor(statusCode: number) {
  if (statusCode >= 200 && statusCode < 300) {
    return 'bg-green-900 text-green-300'
  }
  if (statusCode >= 400 && statusCode < 500) {
    return 'bg-yellow-900 text-yellow-300'
  }
  if (statusCode >= 500) {
    return 'bg-red-900 text-red-300'
  }
  return 'bg-gray-700 text-gray-300'
}
</script>