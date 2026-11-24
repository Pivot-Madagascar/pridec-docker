<template>
  <!-- @container: the fact cards and the two columns follow the page's width (the side menu open or folded). -->
  <div class="@container space-y-6">
    <!-- Page header (shadcn Item): the cycle and its pass, then the pass's actions on the right. -->
    <Item class="p-0" data-test="page-header">
      <ItemContent>
        <ItemTitle><h2 class="text-2xl font-bold">{{ state ? `Cycle ${state.cycle}` : 'Forecast' }}</h2></ItemTitle>
        <!-- The month is chosen on Home (/), with the pass to start or resume. -->
        <ItemDescription class="line-clamp-none">
          <template v-if="state">
            <template v-if="state.pass">
              Pass <span class="font-mono">{{ state.pass.id }}</span> · {{ state.pass.state }} · started by {{ state.pass.started_by ?? '-' }}
            </template>
            <template v-else>not started: the first launch starts it</template>
            · <RouterLink :to="{ name: 'Journal', query: state.pass ? { pass: state.pass.id } : {} }" class="text-primary">Journal</RouterLink>
            <span v-if="state.pass?.state === 'paused'" class="text-warning"> · paused: resume it from <RouterLink :to="{ name: 'Home' }" class="text-primary">Home</RouterLink> or the Journal</span>
          </template>
          <template v-else>Loading the pipeline state…</template>
        </ItemDescription>
      </ItemContent>
      <!-- Stop the cycle for now (resumed from the Journal), or for good. -->
      <ItemActions v-if="active">
        <Button variant="outline" :disabled="busy || state?.lock != null" @click="pendingPause = true">Pause the cycle</Button>
        <Button variant="destructive" :disabled="busy || state?.lock != null" @click="pendingAbandon = true">Abandon the cycle</Button>
      </ItemActions>
    </Item>

    <!-- Where the active pass stands: step / (open run /) item, read from etlhub's statuses (position()), in App's top bar. -->
    <Teleport v-if="active" defer to="#app-crumbs">
      <Breadcrumb data-test="position">
        <BreadcrumbList class="text-sm">
          <template v-for="(crumb, i) in crumbs" :key="i">
            <BreadcrumbSeparator v-if="i" />
            <BreadcrumbItem>
              <!-- The last one leads to the current item: its card, or the open run's steps (goToPosition). -->
              <BreadcrumbLink
                v-if="i === crumbs.length - 1 && target"
                as="button"
                type="button"
                aria-current="page"
                class="font-medium text-foreground underline-offset-4 hover:underline"
                data-test="position-link"
                @click="goToPosition"
              >
                {{ crumb }}
              </BreadcrumbLink>
              <BreadcrumbPage v-else-if="i === crumbs.length - 1">{{ crumb }}</BreadcrumbPage>
              <template v-else>{{ crumb }}</template>
            </BreadcrumbItem>
          </template>
        </BreadcrumbList>
      </Breadcrumb>
    </Teleport>

    <!-- Fact cards (shadcn Card), from etlhub's state only: mode, position, running job, GEE variables of the pass. -->
    <div class="grid items-start gap-4 @xl:grid-cols-2 @5xl:grid-cols-4" data-test="facts">
      <!-- The mode: frozen while the pass is active (chosen on Home with the pass; pausing or abandoning frees it). -->
      <ModeToggle :test-mode="state?.test_mode" :dry-run="state?.dry_run" :disabled="busy || active"
        :frozen="active" @change="setMode" />

      <Card class="gap-3 py-4">
        <CardHeader class="px-4">
          <CardDescription>Where you are</CardDescription>
          <CardTitle class="text-xl">{{ active ? crumbs.at(-1) : state?.pass?.state ?? (state ? 'Not started' : '…') }}</CardTitle>
          <CardAction><span class="fact-icon"><MapPin /></span></CardAction>
        </CardHeader>
        <CardContent v-if="active" class="px-4 text-xs text-muted-foreground">{{ crumbs.slice(0, -1).join(' / ') }}</CardContent>
      </Card>

      <Card class="gap-3 py-4" :class="{ 'border-warning/50 bg-warning/8': state?.lock }" :role="state?.lock ? 'status' : undefined" data-test="lock-card">
        <CardHeader class="px-4">
          <CardDescription>Job running</CardDescription>
          <CardTitle class="text-xl" :class="{ 'text-warning': state?.lock }">{{ state?.lock?.task ?? 'None' }}</CardTitle>
          <CardAction><span class="fact-icon"><Cog :class="{ 'animate-spin': state?.lock }" /></span></CardAction>
        </CardHeader>
        <CardContent class="px-4 text-xs text-muted-foreground">
          <template v-if="state?.lock"><template v-if="state.lock.job_id">{{ state.lock.job_id }} · </template>since {{ state.lock.acquired_at }}. </template>One job at a time, both modes.
        </CardContent>
      </Card>

      <Card class="gap-3 py-4">
        <CardHeader class="px-4">
          <CardDescription>GEE variables</CardDescription>
          <CardTitle class="text-xl">{{ !state?.pass ? '-' : state.pass.gee_variables ? state.pass.gee_variables.split(',').length : 'All' }}</CardTitle>
          <CardAction><span class="fact-icon"><CloudSun /></span></CardAction>
        </CardHeader>
        <CardContent class="px-4 text-xs text-muted-foreground">
          <!-- Chosen on Home when the pass started, fixed for it: what Import GEE imports. -->
          <p v-if="state?.pass" data-test="pass-gee">Import GEE: {{ state.pass.gee_variables?.split(',').join(', ') ?? 'all available variables' }}</p>
          <p v-else>Chosen in Import GEE (Data Import).</p>
        </CardContent>
      </Card>
    </div>

    <!-- The steps, then Recent Activity in a right column (under them on a narrow page). -->
    <div class="grid grid-cols-[minmax(0,1fr)] items-start gap-6 @5xl:grid-cols-[minmax(0,1fr)_clamp(16rem,22cqw,22rem)]">
      <Accordion v-model:open="openSteps" :items="accordionItems">
        <template #content-dataImport>
          <div class="action-grid">
            <!-- Import GEE opens its dialog (the variables to import); the Pivot imports launch at once. -->
            <ActionCard v-for="card in cards('data_import')" :key="card.key" :action="card" @action-click="clickImport" />
            <ActionCard v-if="reviewCard" :action="reviewCard" @action-click="openApproval" />
          </div>
          <div class="imports-approval" data-test="imports-approval">
            <span class="approval-text">
              Imports approval: <strong :class="`status-${approveImports?.status ?? 'pending'}`">{{ approveImports?.status ?? 'pending' }}</strong>
              · choose the Pivot data elements to post to DHIS2, flagged ones after checking them; Details: what DHIS2 has
            </span>
            <Button variant="outline" @click="availability.show()">Details</Button>
          </div>
        </template>

        <template #content-forecast>
          <ForecastRuns
            :state="state"
            :focus="runFocus"
            :busy="busy"
            :server-files="serverFiles"
            :defaults="defaults"
            :upload-file="upload"
            @open="openRun"
            @launch="launchItem"
            @validate="openReport(null, true)"
            @report="(source, disease) => openReport({ source, disease }, false)"
            @delete="name => (pendingDelete = name)"
            @preview="openPreview"
            @use-default="useDefault"
            @abandon="pendingRunAbandon = true"
            @skip="skipAlerts"
          />
        </template>

        <template #content-systemUpdate>
          <div class="action-grid action-grid-4">
            <ActionCard v-for="card in cards('system_update')" :key="card.key" :action="card" @action-click="launchItem" />
          </div>
        </template>
      </Accordion>

      <aside data-test="activity-aside">
        <RecentActivity :activityLog="activityLog" />
      </aside>
    </div>

    <ForecastReportModal v-model="showReportModal" :run="reportRun">
      <template v-if="validating" #footer>
        <Button variant="outline" :disabled="busy" @click="decideFromReport('reject')">Reject</Button>
        <Button :disabled="busy" @click="decideFromReport('approve')">Approve</Button>
      </template>
    </ForecastReportModal>

    <ImportAvailabilityDialog
      :open="availability.open.value"
      :loading="availability.loading.value"
      :error="availability.error.value"
      :report="availability.report.value"
      @close="availability.close"
      @refresh="availability.load(true)"
    />

    <!-- The imports decision, line by line: stays open, each chosen line showing its post state, then offers step ①'s
         Build Analytics. Reject closes it first. -->
    <ImportApprovalDialog
      :open="fetched.open.value"
      :loading="fetched.loading.value"
      :error="fetched.error.value"
      :imports="fetched.imports.value"
      :can-approve="!busy && state?.lock == null && !!approveImports?.launchable"
      :can-reject="!busy && state?.lock == null && approveImports?.status === 'success'"
      :posting="approvalPosting"
      :approved="approveImports?.status === 'success'"
      :can-build="!busy && state?.lock == null && !!buildItem?.launchable"
      @close="fetched.close"
      @refresh="fetched.refresh"
      @approve="elements => decideImportsFromApproval('approve', elements)"
      @reject="decideImportsFromApproval('reject')"
      @build="buildFromApproval"
    />

    <!-- Import GEE: the variables to import, each one's state; stays open while the import runs. -->
    <GeeImportDialog
      :open="gee.open.value"
      :loading="gee.loading.value"
      :error="gee.error.value"
      :variables="gee.variables.value"
      :can-import="!busy && state?.lock == null && !!geeItem?.launchable"
      :importing="geeItem?.status === 'running'"
      @close="gee.close"
      @refresh="gee.refresh"
      @import="importGee"
    />

    <ImpactDialog :pending="pending" :busy="busy" @confirm="confirm" @cancel="cancel" />

    <PreviewDialog
      :open="previewCurrent !== null"
      :title="previewCurrent ? FILE_LABELS[previewCurrent.name] : ''"
      :source="previewCurrent?.source ?? 'server'"
      :loading="previewLoading"
      :error="previewError"
      @close="closePreview"
    >
      <ConfigPreview v-if="previewConfig" :config="previewConfig" />
      <CsvPreview v-else-if="previewCsv" :preview="previewCsv" />
    </PreviewDialog>

    <ConfirmDialog
      :open="pendingDelete !== null"
      :title="`Delete ${pendingDelete ? FILE_LABELS[pendingDelete] : ''}?`"
      confirm-label="Delete"
      :busy="busy"
      @confirm="confirmDelete"
      @cancel="pendingDelete = null"
    >
      The file <strong>input/{{ pendingDelete ? FILE_LABELS[pendingDelete] : '' }}</strong> of the open run will be removed.
      Once it was used, the server asks for a confirmation and the run starts again from "Validate inputs".
    </ConfirmDialog>

    <ConfirmDialog
      :open="pendingPause"
      title="Pause this cycle?"
      confirm-label="Pause"
      @confirm="confirmPause"
      @cancel="pendingPause = false"
    >
      The cycle {{ state?.cycle }} (pass {{ state?.pass?.id }}) stops for now. It can be resumed later from Home or the Journal.
    </ConfirmDialog>

    <ConfirmDialog
      :open="pendingAbandon"
      title="Abandon this cycle?"
      confirm-label="Abandon"
      @confirm="confirmAbandon"
      @cancel="pendingAbandon = false"
    >
      The cycle {{ state?.cycle }} (pass {{ state?.pass?.id }}) stops for good: it cannot be resumed, and its open
      forecast run is abandoned. Its journal stays readable. The month can be run again in a new pass.
    </ConfirmDialog>

    <ConfirmDialog
      :open="pendingRunAbandon"
      :title="`Abandon the run ${state?.run?.couple ?? ''}?`"
      confirm-label="Abandon the run"
      @confirm="confirmRunAbandon"
      @cancel="pendingRunAbandon = false"
    >
      Nothing is published. Its steps go back to "To do", including those already done; the input files are kept.
      The cycle goes on, and this run can be opened again later, from the start. The journal records the abandon.
    </ConfirmDialog>

    <!-- After a pause or an abandon: a short screen before Home (leaveForHome). -->
    <LoadingScreen v-if="leaving" data-test="leaving-screen">{{ leaving }} Back to Home…</LoadingScreen>
  </div>
</template>

<script setup lang="ts">
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from '@/components/ui/breadcrumb'
import { pointTo } from '@/utils/attention'
import type { RunFocus } from '@/views/Dashboard/components/runs'
import { computed, nextTick, ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import LoadingScreen from '@/components/LoadingScreen.vue'
import { skipNextRouteLoading } from '@/router/loading'

import Accordion from '@/views/Dashboard/components/Accordion.vue'
import ActionCard from '@/views/Dashboard/components/ActionCard.vue'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Item, ItemActions, ItemContent, ItemDescription, ItemTitle } from '@/components/ui/item'
import ConfigPreview from '@/views/Dashboard/components/ConfigPreview.vue'
import ConfirmDialog from '@/views/Dashboard/components/ConfirmDialog.vue'
import CsvPreview from '@/views/Dashboard/components/CsvPreview.vue'
import ForecastReportModal from '@/views/Dashboard/components/ForecastReportModal.vue'
import ForecastRuns from '@/views/Dashboard/components/ForecastRuns.vue'
import GeeImportDialog from '@/views/Dashboard/components/GeeImportDialog.vue'
import ImpactDialog from '@/views/Dashboard/components/ImpactDialog.vue'
import ImportAvailabilityDialog from '@/views/Dashboard/components/ImportAvailabilityDialog.vue'
import ImportApprovalDialog from '@/views/Dashboard/components/ImportApprovalDialog.vue'
import ModeToggle from '@/views/Dashboard/components/ModeToggle.vue'
import PreviewDialog from '@/views/Dashboard/components/PreviewDialog.vue'
import RecentActivity from '@/views/Dashboard/components/RecentActivity.vue'

import { useActivityLog } from '@/composables/useActivityLog'
import { useImportAvailability } from '@/composables/useImportAvailability'
import { useFetchedImports } from '@/composables/useFetchedImports'
import { useGeeImports } from '@/composables/useGeeImports'
import { useInputPreview } from '@/composables/useInputPreview'
import { usePipeline } from '@/composables/usePipeline'
import { jobOf, labelOf, position, positionItem, step, toCard } from '@/config/pipeline'
import { ClipboardCheck, CloudSun, Cog, MapPin } from '@lucide/vue'
import type { InputName } from '@/types/inputs'
import type { StepName } from '@/types/pipeline'

const FILE_LABELS: Record<InputName, string> = { config: 'config.json', external_data: 'external_data.csv' }


const { activityLog, addActivity } = useActivityLog()
const {
  state, serverFiles, defaults, busy, pending, refresh, confirm, cancel,
  launch, openRun, abandonRun, decide, decideImports, skipAlerts, setMode, upload, remove, useDefault,
  pause, abandonPass
} = usePipeline(addActivity)
const active = computed(() => state.value?.pass?.state === 'active')
// A mode never shows what happened in the other: the switch empties Recent Activity.
watch(() => state.value?.test_mode, (mode, before) => { if (before !== undefined && mode !== before) activityLog.value = [] })
const crumbs = computed(() => (state.value ? position(state.value) : []))
const target = computed(() => (state.value ? positionItem(state.value) : null))

// The accordion's open steps: the breadcrumb's link reopens the one of the current item.
const openSteps = ref(['dataImport', 'forecast', 'systemUpdate'])
const SECTIONS: Record<StepName, string> = { data_import: 'dataImport', forecast: 'forecast', system_update: 'systemUpdate' }
const runFocus = ref<RunFocus | null>(null)
// The steps' cards: their progress is etlhub's `done` and `accessible`, nothing decided here.
const STEP_TITLES: Record<StepName, string> = { data_import: 'Data Import', forecast: 'Forecasts', system_update: 'System Update' }
const accordionItems = computed(() => (Object.keys(SECTIONS) as StepName[]).map(name => {
  const s = step(state.value, name)
  const progress = !s ? undefined : s.done ? 'Done' : s.accessible ? 'In progress' : 'Not open yet'
  return { id: SECTIONS[name], title: STEP_TITLES[name], progress }
}))

// Goes to the current item; it blinks orange only when no job runs (something to click now).
async function goToPosition() {
  if (!target.value) return
  const { step: name, item } = target.value
  const blink = !state.value?.lock
  if (!openSteps.value.includes(SECTIONS[name])) openSteps.value = [...openSteps.value, SECTIONS[name]]
  if (name === 'forecast') {
    runFocus.value = { item: item.item, blink, at: Date.now() }
    return
  }
  await nextTick()
  // Step ①'s Build Analytics has no card: it is launched from the approval's dialog, opened by its card.
  const card = name === 'data_import' && item.item === 'build_analytics' ? 'approve_imports' : item.item
  pointTo(`[data-section="${SECTIONS[name]}"] [data-item="${card}"]`, blink)
}
const availability = useImportAvailability() // "Details" of Data Import: is the imported data in DHIS2?
const fetched = useFetchedImports(state) // "Review and approve": the Pivot elements fetched (Pinia), to post line by line
const gee = useGeeImports(state) // "Import GEE": the variables to import, each one's state

const {
  current: previewCurrent,
  loading: previewLoading,
  error: previewError,
  config: previewConfig,
  csv: previewCsv,
  open: openPreview,
  close: closePreview
} = useInputPreview()

const showReportModal = ref(false)
const reportRun = ref<{ source: string; disease: string } | null>(null)
const validating = ref(false) // opened by "Read and approve": Approve / Reject under the report
const pendingDelete = ref<InputName | null>(null)
const pendingPause = ref(false)
const pendingAbandon = ref(false)
const pendingRunAbandon = ref(false)

// Step ①'s approve_imports (a decision) and build_analytics (after it) share the "Review and Approve" card.
// Import GEE's card always opens its dialog (to see each variable's state, even while it runs): never inactive.
const cards = (name: StepName) => (step(state.value, name)?.items ?? [])
  .filter(i => name !== 'data_import' || !['approve_imports', 'build_analytics'].includes(i.item))
  .map(i => toCard(i, state.value, busy.value))
  .map(c => (c.key === 'import_gee' ? { ...c, inactive: false, loading: false } : c))
const geeItem = computed(() => step(state.value, 'data_import')?.items.find(i => i.item === 'import_gee'))
const approveImports = computed(() => step(state.value, 'data_import')?.items.find(i => i.item === 'approve_imports'))
const buildItem = computed(() => step(state.value, 'data_import')?.items.find(i => i.item === 'build_analytics'))
// Opens the dialog; once the approval is a success, the card shows Build Analytics' status. Always clickable (to review).
const reviewCard = computed(() => {
  const approval = approveImports.value
  if (!approval) return null
  const shown = approval.status === 'success' && buildItem.value ? buildItem.value : approval
  return {
    ...toCard(shown, state.value, busy.value),
    key: 'approve_imports', label: 'Review and Approve', icon: ClipboardCheck, inactive: false,
    ...(shown !== approval && shown.status === 'pending' ? { statusText: 'Approved: Build Analytics to launch' } : {})
  }
})

// A card's key is its checkpoint ('CSB/Malaria:forecast'); the server resolves which checkpoint a job counts for.
const launchItem = (item: string) => launch(jobOf(item), labelOf(item))
const clickImport = (item: string) => (item === 'import_gee' ? gee.show() : launchItem(item))
// The dialog's choice, kept on the pass by etlhub; a confirmation (relaunch after a success) resends it.
const importGee = (variables: string[]) => launch('import_gee', labelOf('import_gee'), { gee_variables: variables })

// run = null: the open run's report (output/); otherwise the report archived when that run closed.
const openReport = (run: { source: string; disease: string } | null, decide: boolean) => {
  reportRun.value = run
  validating.value = decide
  showReportModal.value = true
}

const decideFromReport = async (decision: 'approve' | 'reject') => {
  showReportModal.value = false
  await decide(decision)
}

// "Approve and post" sent from the dialog: its lines show "Posting…" while etlhub posts (busy, a confirmation included),
// then their post state, read again with the list (useFetchedImports follows approve_imports).
const approvalSent = ref(false)
const approvalPosting = computed(() => approvalSent.value && busy.value)
const openApproval = () => {
  approvalSent.value = false
  fetched.show()
}
const decideImportsFromApproval = async (decision: 'approve' | 'reject', elements: string[] = []) => {
  if (decision === 'reject') fetched.close()
  else approvalSent.value = true
  await decideImports(decision, elements)
}
const buildFromApproval = () => {
  fetched.close()
  void launchItem('build_analytics') // followed by its toast, like a card
}

const confirmDelete = async () => {
  const name = pendingDelete.value
  pendingDelete.value = null
  if (name) await remove(name)
}

// Once the pass is paused or abandoned, nothing is left to do here: back to Home, to start or resume a pass.
const router = useRouter()
const LEAVE_MS = 2000
const leaving = ref<string | null>(null)
const leaveForHome = async (message: string) => {
  leaving.value = message
  await new Promise(resolve => setTimeout(resolve, LEAVE_MS))
  skipNextRouteLoading() // its own 2 s screen replaces the short one between pages
  await router.push({ name: 'Home' })
}

const confirmPause = async () => {
  pendingPause.value = false
  if (await pause()) await leaveForHome('Cycle paused.')
}

const confirmAbandon = async () => {
  pendingAbandon.value = false
  if (state.value?.pass && (await abandonPass(state.value.pass.id))) await leaveForHome('Cycle abandoned.')
}

const confirmRunAbandon = async () => {
  pendingRunAbandon.value = false
  await abandonRun()
}

onMounted(refresh)
</script>

<style scoped>
@reference "../../styles/base.css";

/* The fact cards' tinted icon square (the reference's). */
.fact-icon {
  @apply flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary [&_svg]:size-4;
}

.imports-approval {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
}

.approval-text {
  font-size: 0.8125rem;
  color: var(--muted-foreground);
}

.status-success {
  color: var(--success);
}

.status-error {
  color: var(--destructive);
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin-bottom: 2rem;
}

.action-grid-4 {
  grid-template-columns: repeat(4, 1fr);
}

@media (max-width: 1024px) {
  .action-grid,
  .action-grid-4 {
    grid-template-columns: 1fr;
  }
}
</style>
