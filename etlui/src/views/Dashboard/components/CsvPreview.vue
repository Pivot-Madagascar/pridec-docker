<template>
  <div class="csv-preview">
    <div class="summary">
      <span class="summary-item"><strong>{{ preview.total_rows.toLocaleString() }}</strong> rows</span>
      <span class="summary-item"><strong>{{ preview.columns.length }}</strong> columns</span>
      <span v-if="preview.period_range" class="summary-item">
        <strong>{{ formatPeriod(preview.period_range[0]) }}</strong> → <strong>{{ formatPeriod(preview.period_range[1]) }}</strong>
      </span>
      <span v-if="preview.columns.includes('orgUnit')" class="summary-item">
        <strong>{{ preview.org_units.toLocaleString() }}</strong> orgUnits
      </span>
    </div>

    <div class="table-wrap" tabindex="0" aria-label="CSV preview, scrollable">
      <table class="csv-table">
        <caption class="sr-only">First {{ preview.rows.length }} rows of {{ preview.total_rows }}</caption>
        <thead>
          <tr>
            <th scope="col" class="col-index">#</th>
            <th
              v-for="(column, i) in preview.columns"
              :key="i"
              scope="col"
              :class="{ 'col-sticky-1': i === 0, 'col-sticky-2': i === 1 }"
            >
              {{ column }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, r) in preview.rows" :key="r">
            <td class="col-index">{{ r + 1 }}</td>
            <td
              v-for="(_, i) in preview.columns"
              :key="i"
              :title="row[i]"
              :class="{ 'col-sticky-1': i === 0, 'col-sticky-2': i === 1, numeric: isNumeric(row[i]) }"
            >
              {{ formatCell(row[i] ?? '') }}
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!preview.rows.length" class="empty">No data rows.</p>
    </div>

    <p class="footer">
      Showing the first {{ preview.rows.length.toLocaleString() }} of {{ preview.total_rows.toLocaleString() }} rows.
      Decimals are rounded for display; hover a cell for the full value.
    </p>
  </div>
</template>

<script setup lang="ts">
import type { CsvPreviewData } from '@/types/inputs'
import { formatCell, formatPeriod } from '@/utils/preview'

defineProps<{ preview: CsvPreviewData }>()

const isNumeric = (value: string | undefined) => value !== undefined && /^-?\d+(\.\d+)?$/.test(value)
</script>

<style scoped>
@reference "tailwindcss";

.csv-preview {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  gap: 0.875rem;
}

.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.summary-item {
  padding: 0.375rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.8125rem;
  color: #94a3b8;
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.summary-item strong {
  color: #f1f5f9;
  font-weight: 600;
}

.table-wrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
  border-radius: 0.625rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: #0b1222;
}

.table-wrap:focus-visible {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
}

.csv-table {
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.8125rem;
  white-space: nowrap;
}

.csv-table th,
.csv-table td {
  padding: 0.5rem 0.875rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  text-align: left;
}

.csv-table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #1e293b;
  color: #cbd5e1;
  font-weight: 600;
  font-family: ui-monospace, monospace;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
}

.csv-table tbody tr:nth-child(even) td {
  background: #0f172a;
}

.csv-table tbody tr:nth-child(odd) td {
  background: #0b1222;
}

.csv-table tbody tr:hover td {
  background: #1e293b;
}

.csv-table td {
  color: #e2e8f0;
  max-width: 18rem;
  overflow: hidden;
  text-overflow: ellipsis;
}

.csv-table td.numeric {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* Row number + first two columns stay visible while scrolling sideways. */
.col-index,
.col-sticky-1,
.col-sticky-2 {
  position: sticky;
  z-index: 1;
}

thead .col-index,
thead .col-sticky-1,
thead .col-sticky-2 {
  z-index: 3;
}

.col-index {
  left: 0;
  width: 3.5rem;
  min-width: 3.5rem;
  max-width: 3.5rem;
  color: #64748b !important;
  text-align: right !important;
}

.col-sticky-1 {
  left: 3.5rem;
  width: 9rem;
  min-width: 9rem;
  max-width: 9rem;
}

.col-sticky-2 {
  left: 12.5rem;
  width: 6.5rem;
  min-width: 6.5rem;
  max-width: 6.5rem;
  box-shadow: 4px 0 6px -4px rgba(0, 0, 0, 0.6);
}

.empty {
  padding: 2rem;
  text-align: center;
  color: #64748b;
}

.footer {
  font-size: 0.75rem;
  color: #64748b;
}
</style>
