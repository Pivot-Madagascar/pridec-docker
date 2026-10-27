<template>
  <SideLayout>
    <!-- The months and their passes, newest first: one click shows a pass's journal. In the side panel (SideLayout),
         like Recent Activity on the forecast page. -->
    <template #side>
      <nav aria-label="Cycles" class="space-y-2 rounded-lg border bg-card p-3 shadow-lg">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Cycles</h2>
        <!-- A tree like shadcn's file tree (block sidebar-11: Collapsible, chevron, folder, sub-level with a left rule):
             years, then months, then passes. The newest year, the target month and those of the selected pass start open;
             folded content stays in the DOM. -->
        <Collapsible
          v-for="[year, list] in years"
          :key="year"
          :default-open="year === years[0][0] || year === current?.cycle.slice(0, 4)"
          :unmount-on-hide="false"
          data-test="year"
        >
          <CollapsibleTrigger :class="TREE_TRIGGER">
            <ChevronRight :class="TREE_CHEVRON" /><Folder class="size-4 shrink-0" />{{ year }}
          </CollapsibleTrigger>
          <CollapsibleContent :class="TREE_SUB">
            <Collapsible
              v-for="c in list"
              :key="c.cycle"
              :default-open="c.target || c.cycle === current?.cycle"
              :unmount-on-hide="false"
              data-test="cycle"
            >
              <CollapsibleTrigger :class="TREE_TRIGGER">
                <ChevronRight :class="TREE_CHEVRON" /><Folder class="size-4 shrink-0" />
                <span class="font-semibold">{{ monthName(c.cycle) }}</span>
                <span class="text-xs text-muted-foreground">
                  · {{ c.passes.length }} pass{{ c.passes.length === 1 ? '' : 'es' }}<template v-if="c.target"> · launches go here</template>
                </span>
              </CollapsibleTrigger>
              <CollapsibleContent :class="TREE_SUB">
                <!-- One shadcn Trace line per pass, like Recent Activity: the icon and colour of its state; a click selects
                     the pass (its journal on the right) and unfolds its details. The selected pass starts unfolded. -->
                <Trace v-if="c.passes.length" class="py-1">
                  <TraceCollapsible v-for="p in c.passes" :key="p.id" :default-open="p.id === passId" data-test="pass">
                    <TraceCollapsibleTrigger
                      :aria-current="p.id === passId ? 'true' : undefined"
                      :class="{ 'font-semibold text-foreground': p.id === passId }"
                      @click="select(p.id)"
                    >
                      <TraceLine>
                        <TraceIcon :class="STATE_COLORS[p.state]">
                          <component :is="STATE_ICONS[p.state]" :data-test="`state-${p.state}`" />
                        </TraceIcon>
                        <TraceTitle>
                          {{ p.state }}<span v-if="p.mode === 'test'" class="ml-1 rounded bg-warning/15 px-1.5 text-xs text-warning">test</span>
                        </TraceTitle>
                        <TraceDescription class="font-mono text-xs">{{ p.id }}</TraceDescription>
                      </TraceLine>
                    </TraceCollapsibleTrigger>
                    <TraceCollapsibleContent class="text-xs">
                      <!-- The body of AI Elements' Context (hover card of token usage), inline: one fact per row, the label on the
                           left, the value on the right, a rule between rows; a value too long wraps under its label. -->
                      <dl class="divide-y">
                        <div v-for="row in passDetails(p)" :key="row.label" class="flex flex-wrap items-baseline justify-between gap-x-3 py-1.5">
                          <dt>{{ row.label }}</dt>
                          <dd class="ml-auto font-mono text-foreground">{{ row.value }}</dd>
                        </div>
                      </dl>
                    </TraceCollapsibleContent>
                  </TraceCollapsible>
                </Trace>
                <p v-if="!c.passes.length" class="mt-1 text-xs text-muted-foreground">No pass yet: start one from Home.</p>
              </CollapsibleContent>
            </Collapsible>
          </CollapsibleContent>
        </Collapsible>
        <p v-if="!cycles.length && !loading" class="text-sm text-muted-foreground">No cycle yet.</p>
      </nav>
    </template>

    <div class="min-w-0 space-y-6">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <h1 class="text-2xl font-bold text-foreground">{{ current ? `Journal · ${monthName(current.cycle)} · ${current.state}` : 'Cycle journal' }}</h1>
        <div class="flex flex-wrap items-center gap-2 text-sm">
          <!-- A paused pass: resume it (the Dashboard continues it) or abandon it for good. The server has the last word. -->
          <template v-if="current?.state === 'paused'">
            <Button title="Continue this cycle on the Dashboard" @click="resume(current.id)">Resume</Button>
            <Button variant="destructive" @click="abandoning = true">Abandon</Button>
          </template>
          <!-- Reka refuses '' as an item value: 'all' stands for no filter. -->
          <Select :model-value="step || 'all'" @update:model-value="v => (step = v === 'all' ? '' : String(v))">
            <SelectTrigger aria-label="Step" class="w-40"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All steps</SelectItem>
              <SelectItem v-for="s in STEPS" :key="s" :value="s">{{ s }}</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="secondary" :disabled="loading" @click="refresh">
            {{ loading ? 'Loading...' : 'Refresh' }}
          </Button>
          <!-- etlhub enforces it too (403): the CSV export is for administrators. -->
          <a
            v-if="isAdmin"
            class="rounded-md bg-secondary px-4 py-1.5 text-primary hover:bg-secondary/80"
            :href="csvUrl(passId)"
            :class="{ 'pointer-events-none opacity-50': !passId }"
            download
          >
            Export CSV
          </a>
        </div>
      </div>

      <p class="text-xs text-muted-foreground">
        Every change of the pass (one run of the cycle), newest first unless you reverse it. Refused actions (409) are not events: see Tracking.
        Not seen: the <code>pridec</code> command line, build_analytics launched from DHIS2.
        Test events stay in Redis only and disappear if Redis is flushed.
      </p>

      <div v-if="error" class="rounded-lg border border-destructive/40 bg-destructive/15 p-3 text-sm text-destructive">{{ error }}</div>

      <TablePager
        :sizes="PAGE_SIZES"
        v-model:page-size="settings.pageSize"
        v-model:newest-first="settings.newestFirst"
        v-model:page="page"
        :total-pages="totalPages"
      />

      <div class="overflow-hidden rounded-lg border">
        <Table class="min-w-full">
          <TableHeader class="bg-muted/50">
            <TableRow>
              <TableHead class="px-3 py-2">Time</TableHead>
              <TableHead class="px-3 py-2">Step</TableHead>
              <TableHead class="px-3 py-2">Item</TableHead>
              <TableHead class="px-3 py-2">Event</TableHead>
              <TableHead class="px-3 py-2">Actor</TableHead>
              <TableHead class="px-3 py-2">Request</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="(e, index) in rows"
              :key="index"
              :class="{ 'cursor-pointer hover:bg-muted': hasDetail(e) }"
              @click="hasDetail(e) && (selected = e)"
            >
              <TableCell class="whitespace-nowrap px-3 py-2 text-xs text-muted-foreground">
                {{ formatTime(e.at) }}
                <span v-if="e.mode === 'test'" class="ml-1 rounded bg-warning/15 px-1.5 py-0.5 text-warning">test</span>
              </TableCell>
              <TableCell class="px-3 py-2 text-xs">{{ e.step ?? '-' }}</TableCell>
              <TableCell class="px-3 py-2 font-mono text-xs break-all">{{ e.item ?? '-' }}</TableCell>
              <TableCell class="px-3 py-2">
                <span class="font-semibold" :class="EVENT_COLORS[e.event] ?? 'text-foreground'">{{ e.event }}</span>
                <span v-if="e.detail" class="ml-2 text-xs text-muted-foreground">{{ formatDetail(e.detail) }}</span>
              </TableCell>
              <TableCell class="px-3 py-2 text-xs">{{ e.actor ?? '-' }}</TableCell>
              <TableCell class="whitespace-nowrap px-3 py-2 text-xs">
                <template v-if="e.request">{{ e.request.method }} {{ e.request.status_code }}</template>
                <template v-else>-</template>
              </TableCell>
            </TableRow>
            <TableRow v-if="!shown.length && !loading">
              <TableCell colspan="6" class="px-4 py-6 text-center text-muted-foreground">No event for this pass.</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>

      <!-- Same detail as Tracking: the request, then the job logs. -->
      <RequestDialog
        :open="!!selected"
        :title="selected ? `${selected.event} · ${selected.item ?? selected.cycle}` : ''"
        :request="selected?.request"
        :job-id="selected?.job_id && JOB_EVENTS.has(selected.event) ? selected.job_id : null"
        @close="selected = null"
      />

      <ConfirmDialog :open="abandoning" title="Abandon this cycle?" confirm-label="Abandon" @confirm="confirmAbandon" @cancel="abandoning = false">
        The pass {{ current?.id }} of {{ current ? monthName(current.cycle) : '' }} stops for good: it cannot be resumed, and its
        open forecast run is abandoned. Its journal stays readable. The month can be run again in a new pass.
      </ConfirmDialog>
    </div>
  </SideLayout>
</template>

<script setup lang="ts">
import SideLayout from '@/components/SideLayout.vue'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { computed, onMounted, ref } from 'vue'
import TablePager from '@/components/TablePager.vue'
import { useTablePaging } from '@/composables/useTablePaging'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useJournal } from '@/composables/useJournal'
import type { JournalEvent, JournalPass, PassState } from '@/types/pipeline'
import RequestDialog from '@/views/TrackerView/components/RequestDialog.vue'
import ConfirmDialog from '@/views/Dashboard/components/ConfirmDialog.vue'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { ChevronRight, CircleCheck, CirclePause, CirclePlay, CircleX, Folder } from '@lucide/vue'
import {
  Trace, TraceCollapsible, TraceCollapsibleContent, TraceCollapsibleTrigger, TraceDescription, TraceIcon, TraceLine, TraceTitle
} from '@/components/ui/trace'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const STEPS = ['data_import', 'forecast', 'system_update']
// Events of a real job: they have logs. Uploads and decisions have none. carried_over: the job of an earlier pass.
const JOB_EVENTS = new Set(['launched', 'succeeded', 'failed', 'lock_released', 'carried_over'])
const EVENT_COLORS: Record<string, string> = {
  succeeded: 'text-success',
  failed: 'text-destructive',
  reset: 'text-warning',
  run_abandoned: 'text-warning',
  lock_released: 'text-warning',
  cycle_closed: 'text-success',
  paused: 'text-warning',
  abandoned: 'text-destructive',
  availability_checked: 'text-primary',
  carried_over: 'text-success',
}
const STATE_COLORS: Record<PassState, string> = {
  active: 'text-primary',
  paused: 'text-warning',
  complete: 'text-success',
  abandoned: 'text-destructive',
}
// The unfolded details of a pass in the tree: label, value.
const passDetails = (p: JournalPass) => [
  { label: 'Started by', value: p.started_by ?? '-' },
  { label: 'Started', value: formatTime(p.started_at) },
  { label: 'Events', value: String(p.events) },
  ...(p.last_at ? [{ label: 'Last event', value: formatTime(p.last_at) }] : [])
]
const STATE_ICONS: Record<PassState, typeof CircleCheck> = {
  active: CirclePlay,
  paused: CirclePause,
  complete: CircleCheck,
  abandoned: CircleX,
}

const route = useRoute()
const router = useRouter()
const { cycles, events, loading, error, load, loadCycles, csvUrl, resume, abandon } = useJournal()
const isAdmin = computed(() => useAuthStore().user?.is_admin === true)

// ?pass=<id> (the Dashboard link), else the newest pass of the target month once the list is loaded.
const query = route.query.pass
const passId = ref(typeof query === 'string' && /^[0-9a-f]{8}$/.test(query) ? query : '')
const step = ref('')
const selected = ref<JournalEvent | null>(null)
const abandoning = ref(false)

// The tree's look, after shadcn's file tree (sidebar-11): the chevron turns when its own trigger is open.
const TREE_TRIGGER = 'group/trigger flex w-full items-center gap-1.5 rounded-md px-1.5 py-1 text-left text-sm text-foreground hover:bg-muted'
const TREE_CHEVRON = 'size-4 shrink-0 text-muted-foreground transition-transform group-data-[state=open]/trigger:rotate-90'
const TREE_SUB = 'ml-3.5 border-l pl-2'

// Cycles come newest first: grouping keeps that order, years included.
const years = computed(() => {
  const groups = new Map<string, typeof cycles.value>()
  for (const c of cycles.value) groups.set(c.cycle.slice(0, 4), [...(groups.get(c.cycle.slice(0, 4)) ?? []), c])
  return [...groups]
})
const passes = computed<JournalPass[]>(() => cycles.value.flatMap(c => c.passes))
const current = computed(() => passes.value.find(p => p.id === passId.value))

const shown = computed(() => events.value.filter(e => !step.value || e.step === step.value))
// etlhub sends the journal oldest first; 0 = All, the default.
const PAGE_SIZES = [25, 50, 100, 0]
const { settings, page, rows, totalPages } = useTablePaging('journal', shown, { sizes: PAGE_SIZES, defaultSize: 0, sourceNewestFirst: false })

const hasDetail = (e: JournalEvent) => e.request != null || (e.job_id != null && JOB_EVENTS.has(e.event))
const formatTime = (at: string) => new Date(at).toLocaleString()
const monthName = (c: string) =>
  new Date(Number(c.slice(0, 4)), Number(c.slice(4)) - 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
// Nested objects (an import launch's `params`, kept to carry it over to a later pass) stay out: the CSV export has them.
const formatDetail = (detail: Record<string, unknown>) =>
  Object.entries(detail)
    .filter(([, v]) => Array.isArray(v) || v === null || typeof v !== 'object')
    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : String(v)}`)
    .join(' · ')

function select(id: string) {
  passId.value = id
  router.replace({ query: { ...route.query, pass: id } }) // shareable, kept on reload; Back leaves the page
  load(id)
}

async function refresh() {
  await loadCycles()
  passId.value ||= cycles.value.find(c => c.target)?.passes[0]?.id ?? passes.value[0]?.id ?? ''
  if (passId.value) await load(passId.value)
}

async function confirmAbandon() {
  abandoning.value = false
  if (current.value) await abandon(current.value.id)
}

onMounted(refresh)
</script>
