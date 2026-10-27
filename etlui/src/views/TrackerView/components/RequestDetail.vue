<template>
  <Table class="table-fixed">
    <TableHeader class="text-xs">
      <TableRow>
        <TableHead class="w-20 px-3 py-2 font-normal">Method</TableHead>
        <TableHead class="w-20 px-3 py-2 font-normal">Status</TableHead>
        <TableHead class="px-3 py-2 font-normal">URL</TableHead>
        <TableHead class="w-28 px-3 py-2 font-normal">Duration</TableHead>
        <TableHead class="w-48 px-3 py-2 font-normal">Job ID</TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      <TableRow>
        <TableCell class="px-3 py-2">{{ request.method }}</TableCell>
        <TableCell class="px-3 py-2">
          <span class="rounded px-2 py-0.5 text-xs font-semibold" :class="statusColor(request.status_code)">{{ request.status_code }}</span>
        </TableCell>
        <TableCell class="px-3 py-2 font-mono text-xs break-all">{{ request.url }}</TableCell>
        <TableCell class="px-3 py-2">{{ request.duration_ms.toFixed(2) }} ms</TableCell>
        <TableCell class="px-3 py-2 font-mono text-xs break-all">{{ request.job_id ?? '-' }}</TableCell>
      </TableRow>
      <TableRow v-if="request.reason" class="text-yellow-300">
        <TableCell colspan="5" class="px-3 py-2 text-xs">
          Refused by the pipeline<template v-if="request.code"> ({{ request.code }})</template>: {{ request.reason }}
        </TableCell>
      </TableRow>
    </TableBody>
  </Table>
</template>

<script setup lang="ts">
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { RequestLog } from '@/services/api'
import { statusColor } from '@/utils/status'

defineProps<{
  request: RequestLog
}>()
</script>
