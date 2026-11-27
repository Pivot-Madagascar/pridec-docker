<template>
  <!-- PreviewDialog's frame (header, loader, error, footer); one table per Pivot import, one line per data element. -->
  <PreviewDialog
    :open="open"
    title="Approve the Pivot data to post"
    :loading="loading"
    :error="error"
    loading-label="Reading the fetched data…"
    :busy="posting ? 'Posting to DHIS2…' : undefined"
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
              <TableHead class="num">Values</TableHead>
              <TableHead class="num">Min</TableHead>
              <TableHead class="num">Max</TableHead>
              <TableHead class="num">Missing</TableHead>
              <TableHead class="num">Negative</TableHead>
              <TableHead>Check</TableHead>
              <TableHead>Approval state</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <template v-for="el in imp.elements" :key="el.data_element">
              <TableRow
                :data-element="el.data_element"
                :data-state="selected.has(el.data_element) ? 'selected' : undefined"
                class="cursor-pointer"
                @click="toggle(el.data_element)"
              >
                <TableCell @click.stop>
                  <Checkbox :model-value="selected.has(el.data_element)" :aria-label="`Post ${el.data_element}`" @update:model-value="toggle(el.data_element)" />
                </TableCell>
                <TableCell class="approval-code">{{ el.data_element }}</TableCell>
                <TableCell class="num">{{ el.rows }}</TableCell>
                <template v-if="stats(el.text)">
                  <TableCell class="num" data-test="stat-min">{{ stats(el.text)!.min }}</TableCell>
                  <TableCell class="num" data-test="stat-max">{{ stats(el.text)!.max }}</TableCell>
                  <TableCell class="num" :class="{ 'is-flagged': stats(el.text)!.missing !== '0' }" data-test="stat-missing">{{ stats(el.text)!.missing }}</TableCell>
                  <TableCell class="num" :class="{ 'is-flagged': stats(el.text)!.negative !== '0' }" data-test="stat-negative">{{ stats(el.text)!.negative }}</TableCell>
                </template>
                <!-- Another wording of the check (or no summary): its text as it is. -->
                <TableCell v-else colspan="4" class="approval-message">{{ el.text ?? '' }}</TableCell>
                <TableCell>
                  <span v-if="el.flagged" class="is-flagged">Flagged</span>
                  <span v-else class="is-ok">OK</span>
                </TableCell>
                <TableCell data-test="approval-state" :class="stateClass(el)" :title="el.post?.error ?? undefined">
                  {{ stateOf(el) }}
                </TableCell>
              </TableRow>
              <TableRow v-if="el.flagged" class="cursor-pointer" data-test="approval-problems" @click="toggle(el.data_element)">
                <TableCell />
                <TableCell colspan="8" class="approval-message is-flagged">
                  <span v-for="problem in checkProblems(el.error)" :key="problem" class="block">↳ {{ problem }}</span>
                </TableCell>
              </TableRow>
            </template>
          </TableBody>
        </Table>
      </section>
      <!-- The decision, right under the tables: each chosen line then goes Pending → Posting… → Posted. -->
      <div class="approval-actions" data-test="approval-actions">
        <Button variant="outline" :disabled="!canReject || loading || posting" @click="emit('reject')">Reject</Button>
        <Button :disabled="!canApprove || loading || posting" data-test="approve-imports" @click="approve">
          {{ selected.size ? `Approve and post ${selected.size}` : 'Approve without posting' }}
        </Button>
      </div>
    </template>
    <template #footer>
      <!-- Step ①'s Build Analytics, once the approval is a success; enabled when etlhub allows it. -->
      <Button v-if="approved && !posting" :disabled="!canBuild" data-test="build-analytics" @click="emit('build')">
        Build analytics
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
import type { FetchedElement, FetchedImport } from '@/types/pipeline'
import { checkProblems, parseCheckStats as stats } from '@/utils/checkSummary'
import PreviewDialog from './PreviewDialog.vue'

const props = defineProps<{
  open: boolean
  loading: boolean
  error: string
  imports: FetchedImport[] | null
  canApprove: boolean // approve_imports launchable, no job running
  canReject: boolean // approve_imports in success
  posting: boolean // "Approve and post" sent and its approve_imports job running (no per-line progress to read)
  approved: boolean // approve_imports in success: Build analytics is offered
  canBuild: boolean // build_analytics of step 1 launchable, no job running
}>()

const emit = defineEmits<{
  close: []
  refresh: []
  approve: [elements: string[]]
  reject: []
  build: []
}>()

// The lines to post: every element not flagged, when other lines are read (a new fetch). The same lines read again
// (after an approval, for their post state) keep the choice.
const selected = ref(new Set<string>())
let shownLines: string | null = null
watch(() => props.imports, imports => {
  if (!imports) return
  const lines = imports.flatMap(i => i.elements.map(e => `${e.data_element}:${e.flagged}`)).join()
  if (lines === shownLines) return
  shownLines = lines
  selected.value = new Set(imports.flatMap(i => i.elements.filter(e => !e.flagged).map(e => e.data_element)))
}, { immediate: true })

function toggle(name: string): void {
  const next = new Set(selected.value)
  if (!next.delete(name)) next.add(name)
  selected.value = next
}

// In the dialog's order, not the order of the clicks.
const chosen = () => (props.imports ?? []).flatMap(i => i.elements.map(e => e.data_element)).filter(n => selected.value.has(n))

const sent = ref<string[]>([]) // what "Approve and post" sent: those lines show "Posting…" while it posts
function approve(): void {
  sent.value = chosen()
  emit('approve', sent.value)
}

// A line's approval state: etlhub's `post` once posted (kept with the data), else the choice about to be sent.
const POSTED: Record<string, string> = { posted: 'Posted', empty: 'Nothing to post', failed: 'Failed' }
function stateOf(el: FetchedElement): string {
  if (props.posting && sent.value.includes(el.data_element)) return 'Posting…'
  if (el.post) return POSTED[el.post.status] + (el.post.dry_run && el.post.status !== 'failed' ? ' (dry run)' : '')
  return selected.value.has(el.data_element) ? 'Pending' : '—'
}
const stateClass = (el: FetchedElement) =>
  el.post?.status === 'failed' ? 'is-flagged' : el.post?.status === 'posted' && !props.posting ? 'is-ok' : undefined
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

.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
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

.approval-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}
</style>
