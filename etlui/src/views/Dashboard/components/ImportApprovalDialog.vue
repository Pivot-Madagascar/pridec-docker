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
    <!-- After "Approve and post": the post (etlhub posts synchronously, no progress to read), then its job's logs. -->
    <section v-if="post" class="approval-post" data-test="approval-post">
      <template v-if="post.posting">
        <p class="approval-meta">
          {{ sent.length ? `Posting ${sent.length} data element(s) to DHIS2 with the pass's DRYRUN…` : 'Approving without posting…' }}
        </p>
        <div class="post-bar" role="progressbar" aria-label="Posting to DHIS2" data-test="posting-bar"><span /></div>
        <ul class="post-list">
          <li v-for="name in sent" :key="name" class="approval-code">{{ name }}</li>
        </ul>
      </template>
      <JobLogsPanel v-else-if="post.jobId" :job-id="post.jobId" />
    </section>
    <template v-else-if="imports">
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
              </TableRow>
              <TableRow v-if="el.flagged" class="cursor-pointer" data-test="approval-problems" @click="toggle(el.data_element)">
                <TableCell />
                <TableCell colspan="7" class="approval-message is-flagged">
                  <span v-for="problem in checkProblems(el.error)" :key="problem" class="block">↳ {{ problem }}</span>
                </TableCell>
              </TableRow>
            </template>
          </TableBody>
        </Table>
      </section>
    </template>
    <template #footer>
      <template v-if="!post">
        <Button variant="outline" :disabled="!canReject || loading" @click="emit('reject')">Reject</Button>
        <Button :disabled="!canApprove || loading || !imports" data-test="approve-imports" @click="approve">
          {{ selected.size ? `Approve and post ${selected.size}` : 'Approve without posting' }}
        </Button>
      </template>
      <!-- Step ①'s Build Analytics, once the approval is a success; enabled when etlhub allows it. -->
      <Button v-if="approved && !post?.posting" :disabled="!canBuild" data-test="build-analytics" @click="emit('build')">
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
import type { FetchedImport } from '@/types/pipeline'
import { checkProblems, parseCheckStats as stats } from '@/utils/checkSummary'
import PreviewDialog from './PreviewDialog.vue'
import JobLogsPanel from '@/views/TrackerView/components/JobLogsPanel.vue'

const props = defineProps<{
  open: boolean
  loading: boolean
  error: string
  imports: FetchedImport[] | null
  canApprove: boolean // approve_imports launchable, no job running
  canReject: boolean // approve_imports in success
  post: { posting: boolean; jobId: string | null } | null // after "Approve and post": running, then its job
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

const sent = ref<string[]>([]) // what "Approve and post" sent, listed while it posts
function approve(): void {
  sent.value = chosen()
  emit('approve', sent.value)
}
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

.post-list {
  margin-top: 0.75rem;
  font-size: 0.8125rem;
}

/* Indeterminate: etlhub answers once every element is posted. */
.post-bar {
  @apply h-2 w-full overflow-hidden rounded-full bg-primary/20;
}

.post-bar span {
  @apply block h-full w-2/5 rounded-full bg-primary;
  animation: post-slide 1.2s ease-in-out infinite;
}

@keyframes post-slide {
  from { transform: translateX(-100%); }
  to { transform: translateX(250%); }
}

@media (prefers-reduced-motion: reduce) {
  .post-bar span {
    @apply w-full opacity-60;
    animation: none;
  }
}
</style>
