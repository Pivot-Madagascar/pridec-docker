<template>
  <div class="overflow-hidden rounded-lg border">
    <Table class="min-w-full">
      <TableHeader class="bg-muted/50">
        <TableRow>
          <TableHead class="px-4 py-2 text-left">Request ID</TableHead>
          <TableHead class="px-4 py-2 text-left">Time</TableHead>
          <TableHead class="px-4 py-2 text-left">Method</TableHead>
          <TableHead class="px-4 py-2 text-left">Endpoint</TableHead>
          <TableHead class="px-4 py-2 text-left">Status</TableHead>
          <TableHead class="px-4 py-2 text-right">Duration (ms)</TableHead>
          <TableHead class="px-4 py-2"></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow
          v-for="req in paginated"
          :key="req.request_id"
          :data-state="selectedId === req.request_id ? 'selected' : undefined"
          :style="hasDetail(req) ? 'cursor: pointer' : undefined"
          @click="hasDetail(req) && $emit('select', req.request_id)"
        >
          <TableCell class="px-4 py-2 font-mono text-xs text-foreground">
            {{ shortRequestId(req.request_id) }}
          </TableCell>
          <TableCell class="px-4 py-2 text-xs text-muted-foreground">
            {{ formatTime(req.timestamp) }}
          </TableCell>
          <TableCell class="px-4 py-2">
            <span
              class="inline-block rounded bg-muted px-2 py-0.5 text-xs font-semibold"
            >
              {{ req.method }}
            </span>
          </TableCell>
          <TableCell class="px-4 py-2 font-mono text-xs text-foreground break-all">
            {{ endpointOf(req.url) }}
          </TableCell>
          <TableCell class="px-4 py-2">
            <span
              class="inline-block rounded px-2 py-0.5 text-xs font-semibold"
              :class="statusColor(req.job_status ?? req.status_code)"
            >
              <!-- A job launch shows its job's end, not its 202 -->
              {{ req.job_status ?? req.status_code }}
            </span>
          </TableCell>
          <TableCell class="px-4 py-2 text-right font-mono text-xs text-foreground">
            {{ req.duration_ms.toFixed(2) }}
          </TableCell>
          <TableCell class="px-4 py-2 text-right">
            <!-- Only requests that started a job (their logs) or were refused by the pipeline (the reason) have something to show -->
            <Button v-if="hasDetail(req)" variant="link" size="xs" data-test="detail-btn" @click.stop="$emit('select', req.request_id)">
              Detail
            </Button>
          </TableCell>
        </TableRow>
        <TableRow v-if="!requests.length">
          <TableCell colspan="7" class="px-4 py-6 text-center text-muted-foreground">
            No requests recorded yet.
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>

    <div class="flex items-center justify-end border-t px-4 py-2 space-x-2">
      <Button variant="secondary" size="xs" :disabled="page <= 0" @click="$emit('update:page', page - 1)">Prev</Button>
      <span class="text-xs text-muted-foreground">Page {{ page + 1 }} / {{ totalPages || 1 }}</span>
      <Button variant="secondary" size="xs" :disabled="page + 1 >= totalPages" @click="$emit('update:page', page + 1)">Next</Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { computed } from 'vue'
import type { RequestLog } from '@/services/api'
import { statusColor } from '@/utils/status'
import { Button } from '@/components/ui/button'

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
</script>