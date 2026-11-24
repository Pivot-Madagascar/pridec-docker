<template>
  <!-- PreviewDialog's frame (header, loader, error); one line per GEE variable: its checkbox, then its import state,
       like the Pivot approval's "Approval state". Opened by the Import GEE card; stays open while the import runs. -->
  <PreviewDialog
    :open="open"
    title="Import the GEE variables into DHIS2"
    :loading="loading && !variables"
    :error="error"
    loading-label="Reading the GEE variables…"
    :busy="importing ? 'Importing from GEE…' : undefined"
    data-test="gee-dialog"
    @close="emit('close')"
  >
    <template #actions>
      <Button variant="outline" size="sm" :disabled="loading" data-test="gee-refresh" @click="emit('refresh')">Refresh</Button>
    </template>
    <template v-if="variables">
      <p class="mb-2 text-[0.8125rem] text-muted-foreground">
        The checked variables are fetched from GEE once, then posted to DHIS2 one by one with the pass's DRYRUN: each line
        shows its own state. Your choice is kept for the pass; an unchecked variable is never posted.
      </p>
      <Table class="text-[0.8125rem]">
        <TableHeader>
          <TableRow>
            <TableHead><span class="sr-only">Import</span></TableHead>
            <TableHead>Variable</TableHead>
            <TableHead class="text-right">Values</TableHead>
            <TableHead>Import state</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow
            v-for="v in variables"
            :key="v.variable"
            :data-variable="v.variable"
            :data-state="selected.has(v.variable) ? 'selected' : undefined"
            class="cursor-pointer"
            @click="toggle(v.variable)"
          >
            <TableCell @click.stop>
              <Checkbox :model-value="selected.has(v.variable)" :aria-label="`Import ${v.variable}`" @update:model-value="toggle(v.variable)" />
            </TableCell>
            <TableCell class="font-mono">{{ v.variable }}</TableCell>
            <TableCell class="text-right tabular-nums">{{ v.state?.rows ?? '' }}</TableCell>
            <TableCell data-test="import-state" :class="stateClass(v)" :title="v.state?.error ?? undefined">{{ stateOf(v) }}</TableCell>
          </TableRow>
        </TableBody>
      </Table>
      <!-- Right under the table, like the approval's decision. -->
      <div class="mt-4 flex items-center justify-end gap-3">
        <p v-if="!selected.size" class="text-xs text-destructive">Choose at least one variable.</p>
        <Button :disabled="!canImport || !selected.size || loading" data-test="gee-import" @click="emit('import', chosen())">
          Import {{ selected.size }} variable{{ selected.size === 1 ? '' : 's' }}
        </Button>
      </div>
    </template>
  </PreviewDialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { GeeVariable } from '@/types/pipeline'
import PreviewDialog from './PreviewDialog.vue'

const props = defineProps<{
  open: boolean
  loading: boolean
  error: string
  variables: GeeVariable[] | null
  canImport: boolean // import_gee launchable, no job running
  importing: boolean // import_gee running: the approval's spinner covers the lines (their states stay visible under it)
}>()

const emit = defineEmits<{
  close: []
  refresh: []
  import: [variables: string[]]
}>()

// The lines to import: the pass's choice (all of them until one is made), whenever etlhub's choice changes. Reading the
// same choice again (the states while it imports) keeps the user's clicks.
const selected = ref(new Set<string>())
let shownChoice: string | null = null
watch(() => props.variables, variables => {
  if (!variables) return
  const choice = variables.filter(v => v.chosen).map(v => v.variable).join()
  if (choice === shownChoice) return
  shownChoice = choice
  selected.value = new Set(variables.filter(v => v.chosen).map(v => v.variable))
}, { immediate: true })

function toggle(name: string): void {
  const next = new Set(selected.value)
  if (!next.delete(name)) next.add(name)
  selected.value = next
}

// In the dialog's order (pridec_gee's), not the order of the clicks.
const chosen = () => (props.variables ?? []).map(v => v.variable).filter(n => selected.value.has(n))

// A line's state: etlhub's, of its last import in the pass; else the choice about to be sent.
const DONE: Record<string, string> = { running: 'Importing…', imported: 'Imported', empty: 'Nothing to import', failed: 'Failed' }
function stateOf(v: GeeVariable): string {
  if (v.state) return DONE[v.state.status] + (v.state.dry_run && v.state.status === 'imported' ? ' (dry run)' : '')
  return selected.value.has(v.variable) ? 'Pending' : '—'
}
const stateClass = (v: GeeVariable) =>
  v.state?.status === 'failed' ? 'font-semibold text-destructive' : v.state?.status === 'imported' ? 'font-semibold text-success' : undefined
</script>
