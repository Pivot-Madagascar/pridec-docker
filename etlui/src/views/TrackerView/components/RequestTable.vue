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
          v-for="req in requests"
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
  </div>
</template>

<script setup lang="ts">
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { RequestLog } from '@/services/api'
import { statusColor } from '@/utils/status'
import { Button } from '@/components/ui/button'

defineProps<{
  requests: RequestLog[] // the rows of the current page (TrackerView pages them)
  selectedId?: string | null
}>()

const hasDetail = (req: RequestLog) => req.job_id != null || req.reason != null

defineEmits<{
  (e: 'select', requestId: string): void
}>()

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