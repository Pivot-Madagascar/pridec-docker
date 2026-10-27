<template>
  <!-- PreviewDialog's frame (header, loader, error, footer); only the report is drawn here. -->
  <PreviewDialog
    :open="open"
    title="Imported data in DHIS2"
    :loading="loading"
    :error="error"
    loading-label="Checking DHIS2…"
    class="availability-dialog"
    data-test="availability-dialog"
    @close="emit('close')"
  >
    <template #actions>
      <Button variant="outline" size="sm" :disabled="loading" @click="emit('refresh')">Refresh</Button>
    </template>
    <template v-if="report">
      <p class="availability-meta">
        {{ report.dhis_url }} · last analytics build: <strong>{{ report.last_analytics ? new Date(report.last_analytics).toLocaleString() : 'unknown' }}</strong>
      </p>
      <p class="availability-meta">
        Each cell: organisation units with a stored value, and below, how many the analytics tables have.
        N/A: not imported yet. Analytics behind: run Build Analytics.
        A section checked earlier in this cycle is reused until its import is launched again (30 days at most);
        Refresh checks them all now.
      </p>

      <section v-for="imp in report.imports" :key="imp.task" class="availability-section">
        <h4 class="availability-task">{{ labelOf(imp.task) }} <span class="availability-ou">{{ imp.org_units }}</span></h4>
        <p class="availability-origin" data-test="availability-origin">
          <span v-if="imp.reused" class="availability-badge">reused</span>
          checked {{ new Date(imp.checked_at).toLocaleString() }}<template v-if="imp.checked_by"> by {{ imp.checked_by }}</template>
          <template v-if="imp.pass_id"> · pass {{ imp.pass_id }}</template>
        </p>
        <!-- Table's own container scrolls sideways. The class is on the inner <table>, out of this scope's reach:
             its box styles are utilities here, `.availability-table th/td` still match (TableHead/TableCell are roots). -->
        <div>
          <Table class="availability-table border-collapse text-[0.8125rem]">
            <TableHeader>
              <TableRow>
                <TableHead>Data element</TableHead>
                <TableHead v-for="pe in imp.periods" :key="pe">{{ formatPeriod(pe) }}</TableHead>
                <TableHead><span class="sr-only">Imported</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="el in imp.elements" :key="el.code" :data-code="el.code">
                <TableHead class="availability-code" scope="row">{{ el.code }}</TableHead>
                <TableCell v-if="el.raw === null" :colspan="imp.periods.length" class="is-error">{{ el.error }}</TableCell>
                <template v-else>
                  <TableCell v-for="pe in imp.periods" :key="pe" :class="{ 'is-missing': !el.raw[pe] }">
                    <template v-if="el.raw[pe]">
                      {{ el.raw[pe] }}
                      <span class="availability-analytics" :class="{ 'is-behind': el.analytics && el.analytics[pe] !== el.raw[pe] }">
                        {{ el.analytics ? el.analytics[pe] : '?' }}
                      </span>
                    </template>
                    <template v-else>N/A</template>
                  </TableCell>
                </template>
                <TableCell class="availability-mark">
                  <span v-if="el.imported" class="is-ok" aria-label="Imported">✓</span>
                  <span v-else class="is-ko" aria-label="Not imported">✗</span>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        <p v-for="el in imp.elements.filter(e => e.raw && e.error)" :key="el.code" class="availability-note is-error">
          {{ el.code }}: analytics not checked ({{ el.error }})
        </p>
        <p v-for="el in imp.elements.filter(e => e.analytics_up_to_date === false)" :key="el.code" class="availability-note">
          {{ el.code }}: analytics behind the stored values, run Build Analytics.
        </p>
      </section>
    </template>
    <template v-if="$slots.footer" #footer><slot name="footer" /></template>
  </PreviewDialog>
</template>

<script setup lang="ts">
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { labelOf } from '@/config/pipeline'
import type { ImportAvailabilityReport } from '@/types/pipeline'
import { formatPeriod } from '@/utils/preview'
import PreviewDialog from './PreviewDialog.vue'
import { Button } from '@/components/ui/button'

defineProps<{
  open: boolean
  loading: boolean
  error: string
  report: ImportAvailabilityReport | null
}>()

const emit = defineEmits<{
  close: []
  refresh: []
}>()
</script>

<style scoped>
@reference "../../../styles/base.css";

.availability-meta {
  margin-bottom: 0.5rem;
  font-size: 0.8125rem;
  color: var(--muted-foreground);
}

.availability-section {
  margin-top: 1.25rem;
}

.availability-task {
  margin-bottom: 0.5rem;
  font-weight: 700;
  color: var(--foreground);
}

.availability-ou {
  margin-left: 0.5rem;
  font-family: ui-monospace, monospace;
  font-size: 0.75rem;
  font-weight: 400;
  color: var(--muted-foreground);
  word-break: break-all;
}

.availability-origin {
  margin-bottom: 0.5rem;
  font-size: 0.75rem;
  color: var(--muted-foreground);
}

.availability-badge {
  margin-right: 0.375rem;
  padding: 0.0625rem 0.5rem;
  border-radius: 999px;
  font-weight: 600;
  color: var(--primary);
  background: color-mix(in oklab, var(--primary) 12%, transparent);
}

.availability-table th,
.availability-table td {
  padding: 0.375rem 0.625rem;
  border: 1px solid var(--border);
  text-align: center;
  white-space: nowrap;
}

.availability-table thead th {
  background: var(--muted);
  color: var(--foreground);
}

.availability-code {
  font-family: ui-monospace, monospace;
  font-weight: 400;
  text-align: left !important;
}

.availability-analytics {
  display: block;
  font-size: 0.6875rem;
  color: var(--muted-foreground);
}

.availability-analytics.is-behind {
  color: var(--warning);
}

.is-missing {
  color: var(--muted-foreground);
}

.is-error {
  color: var(--destructive);
  white-space: normal !important;
}

.availability-mark {
  font-size: 1rem;
  font-weight: 700;
}

.is-ok {
  color: var(--success);
}

.is-ko {
  color: var(--destructive);
}

.availability-note {
  margin-top: 0.375rem;
  font-size: 0.75rem;
  color: var(--warning);
}
</style>
