<template>
  <div class="space-y-0">
    <section class="dashboard-section">
      <h2 class="section-header">ETL Pipeline</h2>
      <p class="section-subtitle">
        <template v-if="state">
          Cycle {{ state.cycle }} · {{ state.cycle_state === 'closed' ? 'complete' : `current step: ${state.current_step}` }}
        </template>
        <template v-else>Loading the pipeline state…</template>
      </p>

      <!-- Before step 1: the mode applies to the whole cycle. -->
      <ModeToggle :dry-run="state?.dry_run" :disabled="busy || state?.lock != null" @change="setMode" />

      <div v-if="state?.lock" class="lock-banner" role="status">
        <span>Running: <strong>{{ state.lock.task }}</strong> ({{ state.lock.job_id }}) since {{ state.lock.acquired_at }}. One job at a time.</span>
      </div>

      <Accordion :items="accordionItems" :default-open="['dataImport', 'forecast', 'systemUpdate']">
        <template #content-dataImport>
          <div class="action-grid">
            <ActionCard v-for="card in cards('data_import')" :key="card.key" :action="card" @action-click="launchItem" />
          </div>
          <div class="imports-approval">
            <span class="approval-text">
              Imports approval: <strong :class="`status-${approveImports?.status ?? 'pending'}`">{{ approveImports?.status ?? 'pending' }}</strong>
              · check the case counts first: COM &lt; 100, CSB under the limit
            </span>
            <button type="button" class="approval-btn approval-btn-primary" :disabled="busy || state?.lock != null || !approveImports?.launchable" @click="decideImports('approve')">Approve imports</button>
            <button type="button" class="approval-btn" :disabled="busy || state?.lock != null || approveImports?.status !== 'success'" @click="decideImports('reject')">Reject</button>
          </div>
        </template>

        <template #content-forecast>
          <ForecastRuns
            :state="state"
            :busy="busy"
            :is-admin="!!auth.user?.is_admin"
            :server-files="serverFiles"
            :upload-file="upload"
            @open="openRun"
            @launch="launchItem"
            @validate="openReport(null, true)"
            @report="(source, disease) => openReport({ source, disease }, false)"
            @delete="name => (pendingDelete = name)"
            @preview="openPreview"
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

    <RecentActivity :activityLog="activityLog" />

    <ForecastReportModal v-model="showReportModal" :run="reportRun">
      <template v-if="validating" #footer>
        <button type="button" class="approval-btn" :disabled="busy" @click="decideFromReport('reject')">Reject</button>
        <button type="button" class="approval-btn approval-btn-primary" :disabled="busy" @click="decideFromReport('approve')">Approve</button>
      </template>
    </ForecastReportModal>

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
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'

import Accordion from '@/views/Dashboard/components/Accordion.vue'
import ActionCard from '@/views/Dashboard/components/ActionCard.vue'
import ConfigPreview from '@/views/Dashboard/components/ConfigPreview.vue'
import ConfirmDialog from '@/views/Dashboard/components/ConfirmDialog.vue'
import CsvPreview from '@/views/Dashboard/components/CsvPreview.vue'
import ForecastReportModal from '@/views/Dashboard/components/ForecastReportModal.vue'
import ForecastRuns from '@/views/Dashboard/components/ForecastRuns.vue'
import ImpactDialog from '@/views/Dashboard/components/ImpactDialog.vue'
import ModeToggle from '@/views/Dashboard/components/ModeToggle.vue'
import PreviewDialog from '@/views/Dashboard/components/PreviewDialog.vue'
import RecentActivity from '@/views/Dashboard/components/RecentActivity.vue'

import { useActivityLog } from '@/composables/useActivityLog'
import { useInputPreview } from '@/composables/useInputPreview'
import { usePipeline } from '@/composables/usePipeline'
import { jobOf, labelOf, step, toCard } from '@/config/pipeline'
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
  state, serverFiles, busy, pending, refresh, confirm, cancel,
  launch, openRun, abandonRun, decide, decideImports, setMode, releaseLock, upload, remove
} = usePipeline(addActivity)

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

// approve_imports is a decision (Approve / Reject buttons), not a job card.
const cards = (name: StepName) =>
  (step(state.value, name)?.items ?? []).filter(i => i.item !== 'approve_imports').map(i => toCard(i, state.value, busy.value))
const approveImports = computed(() => step(state.value, 'data_import')?.items.find(i => i.item === 'approve_imports'))

// A card's key is its checkpoint ('CSB/Malaria:forecast'); the server resolves which checkpoint a job counts for.
const launchItem = (item: string) => launch(jobOf(item), labelOf(item))

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

const confirmDelete = async () => {
  const name = pendingDelete.value
  pendingDelete.value = null
  if (name) await remove(name)
}

const confirmRelease = async () => {
  pendingRelease.value = false
  await releaseLock()
}

onMounted(refresh)
</script>

<style scoped>
@reference "tailwindcss";

.dashboard-section {
  background: #0f172a;
  border-radius: 1rem;
  padding: 2rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.section-header {
  font-size: 1.5rem;
  font-weight: 700;
  color: #f1f5f9;
  margin-bottom: 0.25rem;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.section-subtitle {
  color: #94a3b8;
  font-size: 0.875rem;
  margin-bottom: 1.5rem;
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
  color: #94a3b8;
}

.approval-btn {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  cursor: pointer;
}

.approval-btn-primary {
  background: #4f46e5;
  border-color: #4f46e5;
  color: #fff;
}

.approval-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.status-success {
  color: #34d399;
}

.status-error {
  color: #f87171;
}

.lock-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  margin-bottom: 1.5rem;
  border-radius: 0.75rem;
  background: rgba(251, 191, 36, 0.1);
  border: 1px solid rgba(251, 191, 36, 0.4);
  color: #fde68a;
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
