<template>
  <!-- PreviewDialog's frame (header, loader, error, footer); one table per Pivot import, one line per data element. -->
  <PreviewDialog
    :open="open"
    title="Approve the Pivot data to post"
    :loading="loading"
    :error="error"
    loading-label="Reading the fetched data…"
    class="approval-dialog"
    data-test="approval-dialog"
    @close="emit('close')"
  >
    <template #actions>
      <Button variant="outline" size="sm" :disabled="loading" data-test="approval-refresh" @click="emit('refresh')">Refresh</Button>
    </template>
    <template v-if="imports">
      <p class="approval-meta">
        One line per data element fetched from Pivot in this pass. The checked lines are posted to DHIS2 with the pass's
        DRYRUN when you approve; flagged lines start unchecked. Approving with no line checked posts nothing.
      </p>
      <section v-for="imp in imports" :key="imp.task" class="approval-section">
        <h4 class="approval-task">{{ labelOf(imp.task) }}</h4>
        <p v-if="!imp.elements.length" class="approval-empty" data-test="approval-empty">Nothing fetched in this pass: launch it first.</p>
        <Table v-else class="approval-table text-[0.8125rem]">
          <TableHeader>
            <TableRow>
              <TableHead><span class="sr-only">Post</span></TableHead>
              <TableHead>Data element</TableHead>
              <TableHead>Values</TableHead>
              <TableHead>Check</TableHead>
              <TableHead>Message</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="el in imp.elements"
              :key="el.data_element"
              :data-element="el.data_element"
              :data-state="selected.has(el.data_element) ? 'selected' : undefined"
              class="cursor-pointer"
              @click="toggle(el.data_element)"
            >
              <TableCell @click.stop>
                <Checkbox :model-value="selected.has(el.data_element)" :aria-label="`Post ${el.data_element}`" @update:model-value="toggle(el.data_element)" />
              </TableCell>
              <TableCell class="approval-code">{{ el.data_element }}</TableCell>
              <TableCell>{{ el.rows }}</TableCell>
              <TableCell>
                <span v-if="el.flagged" class="is-flagged">Flagged</span>
                <span v-else class="is-ok">OK</span>
              </TableCell>
              <TableCell class="approval-message" :class="{ 'is-flagged': el.flagged }">{{ el.error ?? el.text ?? '' }}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </section>
    </template>
    <template #footer>
      <Button variant="outline" :disabled="!canReject || loading" @click="emit('reject')">Reject</Button>
      <Button :disabled="!canApprove || loading || !imports" data-test="approve-imports" @click="emit('approve', chosen())">
        {{ selected.size ? `Approve and post ${selected.size}` : 'Approve without posting' }}
      </Button>
    </template>
  </PreviewDialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { labelOf } from '@/config/pipeline'
import type { FetchedImport } from '@/types/pipeline'
import PreviewDialog from './PreviewDialog.vue'

const props = defineProps<{
  open: boolean
  loading: boolean
  error: string
  imports: FetchedImport[] | null
  canApprove: boolean // approve_imports launchable, no job running
  canReject: boolean // approve_imports in success
}>()

const emit = defineEmits<{
  close: []
  refresh: []
  approve: [elements: string[]]
  reject: []
}>()

// The lines to post: every element not flagged, each time the data is read.
const selected = ref(new Set<string>())
watch(() => props.imports, imports => {
  selected.value = new Set((imports ?? []).flatMap(i => i.elements.filter(e => !e.flagged).map(e => e.data_element)))
}, { immediate: true })

function toggle(name: string): void {
  const next = new Set(selected.value)
  if (!next.delete(name)) next.add(name)
  selected.value = next
}

// In the dialog's order, not the order of the clicks.
const chosen = () => (props.imports ?? []).flatMap(i => i.elements.map(e => e.data_element)).filter(n => selected.value.has(n))
</script>

<style scoped>
@reference "../../../styles/base.css";

.approval-meta {
  margin-bottom: 0.5rem;
  font-size: 0.8125rem;
  color: var(--muted-foreground);
}

.approval-section {
  margin-top: 1.25rem;
}

.approval-task {
  margin-bottom: 0.5rem;
  font-weight: 700;
  color: var(--foreground);
}

.approval-empty {
  font-size: 0.8125rem;
  color: var(--muted-foreground);
}

.approval-code {
  font-family: ui-monospace, monospace;
}

.approval-message {
  white-space: normal;
  font-size: 0.75rem;
}

.is-ok {
  font-weight: 600;
  color: var(--success);
}

.is-flagged {
  font-weight: 600;
  color: var(--destructive);
}

.approval-message.is-flagged {
  font-weight: 400;
}
</style>
