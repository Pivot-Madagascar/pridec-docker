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
        <div class="availability-scroll">
          <table class="availability-table">
            <thead>
              <tr>
                <th>Data element</th>
                <th v-for="pe in imp.periods" :key="pe">{{ formatPeriod(pe) }}</th>
                <th><span class="sr-only">Imported</span></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="el in imp.elements" :key="el.code" :data-code="el.code">
                <th class="availability-code" scope="row">{{ el.code }}</th>
                <td v-if="el.raw === null" :colspan="imp.periods.length" class="is-error">{{ el.error }}</td>
                <template v-else>
                  <td v-for="pe in imp.periods" :key="pe" :class="{ 'is-missing': !el.raw[pe] }">
                    <template v-if="el.raw[pe]">
                      {{ el.raw[pe] }}
                      <span class="availability-analytics" :class="{ 'is-behind': el.analytics && el.analytics[pe] !== el.raw[pe] }">
                        {{ el.analytics ? el.analytics[pe] : '?' }}
                      </span>
                    </template>
                    <template v-else>N/A</template>
                  </td>
                </template>
                <td class="availability-mark">
                  <span v-if="el.imported" class="is-ok" aria-label="Imported">✓</span>
                  <span v-else class="is-ko" aria-label="Not imported">✗</span>
                </td>
              </tr>
            </tbody>
          </table>
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
@reference "tailwindcss";

.availability-meta {
  margin-bottom: 0.5rem;
  font-size: 0.8125rem;
  color: #94a3b8;
}

.availability-section {
  margin-top: 1.25rem;
}

.availability-task {
  margin-bottom: 0.5rem;
  font-weight: 700;
  color: #f1f5f9;
}

.availability-ou {
  margin-left: 0.5rem;
  font-family: ui-monospace, monospace;
  font-size: 0.75rem;
  font-weight: 400;
  color: #64748b;
  word-break: break-all;
}

.availability-origin {
  margin-bottom: 0.5rem;
  font-size: 0.75rem;
  color: #94a3b8;
}

.availability-badge {
  margin-right: 0.375rem;
  padding: 0.0625rem 0.5rem;
  border-radius: 999px;
  font-weight: 600;
  color: #93c5fd;
  background: rgba(59, 130, 246, 0.12);
}

.availability-scroll {
  overflow-x: auto;
}

.availability-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.availability-table th,
.availability-table td {
  padding: 0.375rem 0.625rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  text-align: center;
  white-space: nowrap;
}

.availability-table thead th {
  background: #1e293b;
  color: #cbd5e1;
}

.availability-code {
  font-family: ui-monospace, monospace;
  font-weight: 400;
  text-align: left !important;
}

.availability-analytics {
  display: block;
  font-size: 0.6875rem;
  color: #64748b;
}

.availability-analytics.is-behind {
  color: #fbbf24;
}

.is-missing {
  color: #64748b;
}

.is-error {
  color: #f87171;
  white-space: normal !important;
}

.availability-mark {
  font-size: 1rem;
  font-weight: 700;
}

.is-ok {
  color: #4ade80;
}

.is-ko {
  color: #f87171;
}

.availability-note {
  margin-top: 0.375rem;
  font-size: 0.75rem;
  color: #fbbf24;
}
</style>
