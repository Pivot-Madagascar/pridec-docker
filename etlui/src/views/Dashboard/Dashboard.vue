<template>
  <SideLayout>
    <!-- The side panel (SideLayout: fixed on the left, like the Journal's cycles). -->
    <template #side>
      <div data-test="activity-aside">
        <RecentActivity :activityLog="activityLog" class="shadow-lg" />
        <!-- Under Recent Activity: stop the cycle for now (resumed from the Journal), or for good. -->
        <div v-if="active" class="pass-actions">
          <Button variant="outline" :disabled="busy || state?.lock != null" @click="pause">Pause the cycle</Button>
          <Button variant="destructive" :disabled="busy || state?.lock != null" @click="pendingAbandon = true">
            Abandon the cycle
          </Button>
        </div>
      </div>
    </template>

    <section class="dashboard-section">
      <h2 class="section-header">ETL Pipeline</h2>
      <div class="section-subtitle flex flex-wrap items-center gap-x-1">
        <template v-if="state">
          <!-- The month is chosen on Home (/), with the pass to start or resume. -->
          Cycle <strong class="cycle-value">{{ state.cycle }}</strong>
          <template v-if="state.pass">
            ·
            <!-- Where the active pass stands: step / (open run /) item, read from etlhub's statuses (position()). -->
            <Breadcrumb v-if="state.pass.state === 'active'" data-test="position">
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
            <template v-else>{{ state.pass.state }}</template>
            · started by {{ state.pass.started_by ?? '-' }}
          </template>
          <template v-else> · not started: the first launch starts it</template>
          · <RouterLink :to="{ name: 'Journal', query: state.pass ? { pass: state.pass.id } : {} }" class="journal-link">Journal</RouterLink>
          <span v-if="state.pass?.state === 'paused'" class="paused-note"> · paused: resume it from <RouterLink :to="{ name: 'Home' }" class="journal-link">Home</RouterLink> or the Journal</span>
        </template>
        <template v-else>Loading the pipeline state…</template>
      </div>

      <!-- Before step 1: the mode applies to the whole cycle. -->
      <ModeToggle :test-mode="state?.test_mode" :dry-run="state?.dry_run" :disabled="busy || state?.lock != null" @change="setMode" />

      <div v-if="state?.lock" class="lock-banner" role="status">
        <span>Running: <strong>{{ state.lock.task }}</strong> ({{ state.lock.job_id }}) since {{ state.lock.acquired_at }}. One job at a time.</span>
      </div>

      <Accordion v-model:open="openSteps" :items="accordionItems">
        <template #content-dataImport>
          <div class="action-grid">
            <ActionCard v-for="card in cards('data_import')" :key="card.key" :action="card" @action-click="launchItem" />
          </div>
          <div class="imports-approval" data-test="imports-approval">
            <span class="approval-text">
              Imports approval: <strong :class="`status-${approveImports?.status ?? 'pending'}`">{{ approveImports?.status ?? 'pending' }}</strong>
              · check the case counts first: COM &lt; 100, CSB under the limit, then approve or reject under the Details
            </span>
            <Button variant="outline" data-item="approve_imports" @click="availability.show()">Details</Button>
          </div>
        </template>

        <template #content-forecast>
          <ForecastRuns
            :state="state"
            :focus="runFocus"
            :busy="busy"
            :is-admin="!!auth.user?.is_admin"
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
            @abandon="abandonRun"
            @release="pendingRelease = true"
          />
        </template>

        <template #content-systemUpdate>
          <div class="action-grid action-grid-4">
            <ActionCard v-for="card in cards('system_update')" :key="card.key" :action="card" @action-click="launchItem" />
          </div>
        </template>
      </Accordion>
    </section>

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
    >
      <!-- The imports decision, under the report it is made on: closes it, then sends the decision (as decideFromReport). -->
      <template #footer>
        <Button variant="outline" :disabled="busy || state?.lock != null || availability.loading.value || approveImports?.status !== 'success'" @click="decideImportsFromDetails('reject')">Reject</Button>
        <Button :disabled="busy || state?.lock != null || availability.loading.value || !approveImports?.launchable" @click="decideImportsFromDetails('approve')">Approve imports</Button>
      </template>
    </ImportAvailabilityDialog>

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
      :open="pendingRelease"
      title="Release the job lock?"
      confirm-label="Release"
      :busy="busy"
      @confirm="confirmRelease"
      @cancel="pendingRelease = false"
    >
      Only when the worker of <strong>{{ state?.lock?.task }}</strong> is dead: the lock never expires on its own.
      The running item becomes "error" and can be relaunched.
    </ConfirmDialog>
  </SideLayout>
</template>

<script setup lang="ts">
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from '@/components/ui/breadcrumb'
import { pointTo } from '@/utils/attention'
import type { RunFocus } from '@/views/Dashboard/components/runs'
import SideLayout from '@/components/SideLayout.vue'
import { computed, nextTick, ref, onMounted } from 'vue'

import Accordion from '@/views/Dashboard/components/Accordion.vue'
import ActionCard from '@/views/Dashboard/components/ActionCard.vue'
import { Button } from '@/components/ui/button'
import ConfigPreview from '@/views/Dashboard/components/ConfigPreview.vue'
import ConfirmDialog from '@/views/Dashboard/components/ConfirmDialog.vue'
import CsvPreview from '@/views/Dashboard/components/CsvPreview.vue'
import ForecastReportModal from '@/views/Dashboard/components/ForecastReportModal.vue'
import ForecastRuns from '@/views/Dashboard/components/ForecastRuns.vue'
import ImpactDialog from '@/views/Dashboard/components/ImpactDialog.vue'
import ImportAvailabilityDialog from '@/views/Dashboard/components/ImportAvailabilityDialog.vue'
import ModeToggle from '@/views/Dashboard/components/ModeToggle.vue'
import PreviewDialog from '@/views/Dashboard/components/PreviewDialog.vue'
import RecentActivity from '@/views/Dashboard/components/RecentActivity.vue'

import { useActivityLog } from '@/composables/useActivityLog'
import { useImportAvailability } from '@/composables/useImportAvailability'
import { useInputPreview } from '@/composables/useInputPreview'
import { usePipeline } from '@/composables/usePipeline'
import { jobOf, labelOf, position, positionItem, step, toCard } from '@/config/pipeline'
import { useAuthStore } from '@/stores/auth'
import type { InputName } from '@/types/inputs'
import type { StepName } from '@/types/pipeline'

const FILE_LABELS: Record<InputName, string> = { config: 'config.json', external_data: 'external_data.csv' }

const accordionItems = [
  { id: 'dataImport', title: 'Data Import' },
  { id: 'forecast', title: 'Forecasts' },
  { id: 'systemUpdate', title: 'System Update' }
]

const { activityLog, addActivity } = useActivityLog()
const {
  state, serverFiles, defaults, busy, pending, refresh, confirm, cancel,
  launch, openRun, abandonRun, decide, decideImports, skipAlerts, setMode, releaseLock, upload, remove, useDefault,
  pause, abandonPass
} = usePipeline(addActivity)
const active = computed(() => state.value?.pass?.state === 'active')
const crumbs = computed(() => (state.value ? position(state.value) : []))
const target = computed(() => (state.value ? positionItem(state.value) : null))

// The accordion's open steps: the breadcrumb's link reopens the one of the current item.
const openSteps = ref(['dataImport', 'forecast', 'systemUpdate'])
const SECTIONS: Record<StepName, string> = { data_import: 'dataImport', forecast: 'forecast', system_update: 'systemUpdate' }
const runFocus = ref<RunFocus | null>(null)

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
  pointTo(`[data-section="${SECTIONS[name]}"] [data-item="${item.item}"]`, blink) // approve_imports: its Details button
}
const availability = useImportAvailability() // "Details" of Data Import: is the imported data in DHIS2?

const {
  current: previewCurrent,
  loading: previewLoading,
  error: previewError,
  config: previewConfig,
  csv: previewCsv,
  open: openPreview,
  close: closePreview
} = useInputPreview()
const auth = useAuthStore()

const showReportModal = ref(false)
const reportRun = ref<{ source: string; disease: string } | null>(null)
const validating = ref(false) // opened by "Read and approve": Approve / Reject under the report
const pendingDelete = ref<InputName | null>(null)
const pendingRelease = ref(false)
const pendingAbandon = ref(false)

// approve_imports is a decision (Approve / Reject buttons), not a job card.
const cards = (name: StepName) =>
  (step(state.value, name)?.items ?? []).filter(i => i.item !== 'approve_imports').map(i => toCard(i, state.value, busy.value))
const approveImports = computed(() => step(state.value, 'data_import')?.items.find(i => i.item === 'approve_imports'))

// A card's key is its checkpoint ('CSB/Malaria:forecast'); the server resolves which checkpoint a job counts for.
// ponytail: calc_orgunit_alerts has no script yet (501): its button skips it (LevelColumn 'Skip').
const launchItem = (item: string) => (jobOf(item) === 'calc_orgunit_alerts' ? skipAlerts() : launch(jobOf(item), labelOf(item)))

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

const decideImportsFromDetails = async (decision: 'approve' | 'reject') => {
  availability.close()
  await decideImports(decision)
}

const confirmDelete = async () => {
  const name = pendingDelete.value
  pendingDelete.value = null
  if (name) await remove(name)
}

const confirmAbandon = async () => {
  pendingAbandon.value = false
  if (state.value?.pass) await abandonPass(state.value.pass.id)
}

const confirmRelease = async () => {
  pendingRelease.value = false
  await releaseLock()
}

onMounted(refresh)
</script>

<style scoped>
@reference "../../styles/base.css";

.dashboard-section {
  background: var(--card);
  border-radius: 1rem;
  padding: 2rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  border: 1px solid var(--border);
}

.section-header {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--foreground);
  margin-bottom: 0.25rem;
}

.section-subtitle {
  color: var(--muted-foreground);
  font-size: 0.875rem;
  margin-bottom: 1.5rem;
}

.cycle-value {
  color: var(--foreground);
}

.journal-link {
  color: var(--primary);
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


.pass-actions {
  @apply mt-3 flex flex-col gap-2;
}

.paused-note {
  color: var(--warning);
}


.status-success {
  color: var(--success);
}

.status-error {
  color: var(--destructive);
}

.lock-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  margin-bottom: 1.5rem;
  border-radius: 0.75rem;
  background: color-mix(in oklab, var(--warning) 10%, transparent);
  border: 1px solid color-mix(in oklab, var(--warning) 40%, transparent);
  color: var(--warning);
  font-size: 0.875rem;
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
