<template>
  <div class="overflow-hidden rounded-lg border border-gray-700">
    <table class="min-w-full text-sm">
      <thead class="bg-gray-800 text-gray-200">
        <tr>
          <th class="px-4 py-2 text-left">Request ID</th>
          <th class="px-4 py-2 text-left">Time</th>
          <th class="px-4 py-2 text-left">Method</th>
          <th class="px-4 py-2 text-left">Endpoint</th>
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
          :style="hasDetail(req) ? 'cursor: pointer' : undefined"
          @click="hasDetail(req) && $emit('select', req.request_id)"
        >
          <td class="px-4 py-2 font-mono text-xs text-gray-300">
            {{ shortRequestId(req.request_id) }}
          </td>
          <td class="px-4 py-2 text-xs text-gray-400">
            {{ formatTime(req.timestamp) }}
          </td>
          <td class="px-4 py-2">
            <span
              class="inline-block rounded px-2 py-0.5 text-xs font-semibold"
              :class="methodColor(req.method)"
            >
              {{ req.method }}
            </span>
          </td>
          <td class="px-4 py-2 font-mono text-xs text-gray-300 break-all">
            {{ endpointOf(req.url) }}
          </td>
          <td class="px-4 py-2">
            <span
              class="inline-block rounded px-2 py-0.5 text-xs font-semibold"
              :class="statusColor(req.job_status ?? req.status_code)"
            >
              <!-- A job launch shows its job's end, not its 202 -->
              {{ req.job_status ?? req.status_code }}
            </span>
          </td>
          <td class="px-4 py-2 text-right font-mono text-xs text-gray-300">
            {{ req.duration_ms.toFixed(2) }}
          </td>
          <td class="px-4 py-2 text-right">
            <!-- Only requests that started a job (their logs) or were refused by the pipeline (the reason) have something to show -->
            <button
              v-if="hasDetail(req)"
              data-test="detail-btn" class="detail-btn text-xs text-blue-400 hover:text-blue-300"
              @click.stop="$emit('select', req.request_id)"
            >
              Detail
            </button>
          </td>
        </tr>
        <tr v-if="!requests.length">
          <td colspan="7" class="px-4 py-6 text-center text-gray-500">
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
import { statusColor } from '@/utils/status'

const PAGE_SIZE = 10
const props = defineProps<{
  requests: RequestLog[]
  selectedId?: string | null
  page: number
}>()

const hasDetail = (req: RequestLog) => req.job_id != null || req.reason != null

defineEmits<{
  (e: 'select', requestId: string): void
  (e: 'update:page', page: number): void
}>()

const paginated = computed(() => props.requests.slice(props.page * PAGE_SIZE, (props.page + 1) * PAGE_SIZE))

const totalPages = computed(() => Math.max(1, Math.ceil(props.requests.length / PAGE_SIZE)))

function shortRequestId(requestId: string) {
  return requestId.length > 12 ? requestId.slice(0, 12) + '...' : requestId
}

function formatTime(timestamp: string | null | undefined) {
  return timestamp ? new Date(timestamp).toLocaleString() : '-'
}

// Path only: the host is always etlhub, and the query string can be long.
function endpointOf(url: string) {
  try {
    return new URL(url).pathname
  } catch {
    return url
  }
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
</script>