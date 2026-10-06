<template>
  <div class="space-y-0">
    <!-- <HeroSection /> -->

    <section class="dashboard-section">
      <h2 class="section-header">ETL Pipeline</h2>
      <p class="section-subtitle">Follow the workflow step by step</p>

      <Accordion :items="accordionItems" :default-open="['dataImport', 'forecastCreation', 'systemUpdate']">
        <template #content-dataImport>
          <div class="data-import-section">
            <div class="action-grid" :class="{ gapless: dataImportActions.length <= 2 }">
              <ActionCard
                v-for="action in dataImportActions"
                :key="action.key"
                :action="action"
                @action-click="handleActionClick"
              />
            </div>
          </div>
        </template>

        <template #content-externalData>
          <div class="external-data-section">
            <p class="upload-intro">Each file is uploaded on its own: drop or browse a file, preview it, then upload it.</p>
            <div class="upload-grid">
              <FileDropzone
                v-for="field in uploadFields"
                :key="field.key"
                v-model="uploadFiles[field.key]"
                :label="field.label"
                :description="field.description"
                :accept="field.accept"
                :server-file="serverFiles[field.key]"
                :deleting="deleting === field.key"
                :uploading="uploading === field.key"
                @upload="file => handleUpload(field.key, file)"
                @delete="pendingDelete = field"
                @preview-local="file => openPreview(field.key, file)"
                @preview-server="openPreview(field.key, 'server')"
              />
            </div>
          </div>
        </template>

        <template #content-forecastCreation>
          <div class="forecast-creation-section">
            <StepperCarousel :steps="pipelineSteps" :initial-step="0" @action-click="handleActionClick" @step-change="handleStepChange">
              <template #step-1>
                <ForecastConfigForm />
              </template>
            </StepperCarousel>
          </div>
        </template>

        <template #content-systemUpdate>
          <div class="system-update-section">
            <div class="action-grid" :class="{ gapless: systemUpdateActions.length <= 2 }">
              <ActionCard
                v-for="action in systemUpdateActions"
                :key="action.key"
                :action="action"
                @action-click="handleActionClick"
              />
            </div>
          </div>
        </template>
      </Accordion>
    </section>

    <Notifications 
      :notification="notification"
      :notificationType="notificationType"
    />

    <RecentActivity :activityLog="activityLog" />

    <ForecastModal 
      v-model="showForecastModal"
      @job-created="handleForecastJobCreated"
    />

    <ForecastReportModal 
      v-model="showReportModal"
    />

    <PreviewDialog
      :open="previewCurrent !== null"
      :title="previewCurrent ? fieldLabel(previewCurrent.name) : ''"
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
      :title="`Delete ${pendingDelete?.label ?? ''}?`"
      confirm-label="Delete"
      :busy="deleting !== null"
      @confirm="confirmDelete"
      @cancel="pendingDelete = null"
    >
      The file <strong>input/{{ pendingDelete?.label }}</strong> will be removed from the server. This cannot be undone.
      <template v-if="pendingDelete?.key === 'config'">
        "Validate inputs" will fail until a new config.json is uploaded.
      </template>
      <template v-else>
        Run "Validate inputs" again so the forecast stops using it.
      </template>
    </ConfirmDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

import Accordion from '@/views/LandingPage/components/Accordion.vue'
import Notifications from '@/views/LandingPage/components/Notifications.vue'
import RecentActivity from '@/views/LandingPage/components/RecentActivity.vue'
import StepperCarousel from '@/views/LandingPage/components/StepperCarousel.vue'
import ForecastModal from '@/views/LandingPage/components/ForecastModal.vue'
import ForecastReportModal from '@/views/LandingPage/components/ForecastReportModal.vue'
import ForecastConfigForm from '@/views/LandingPage/components/ForecastConfigForm.vue'
import ActionCard from '@/views/LandingPage/components/ActionCard.vue'
import FileDropzone from '@/views/LandingPage/components/FileDropzone.vue'
import ConfirmDialog from '@/views/LandingPage/components/ConfirmDialog.vue'
import PreviewDialog from '@/views/LandingPage/components/PreviewDialog.vue'
import ConfigPreview from '@/views/LandingPage/components/ConfigPreview.vue'
import CsvPreview from '@/views/LandingPage/components/CsvPreview.vue'

import { useNotification } from '@/composables/useNotification'
import { useActivityLog } from '@/composables/useActivityLog'
import { useEtlPipeline } from '@/composables/useEtlPipeline'
import { useInputUpload } from '@/composables/useInputUpload'
import { useInputPreview } from '@/composables/useInputPreview'
import { useForecastConfigStore } from '@/stores/forecastConfig'
import { buildDataImportActions, buildPipelineSteps, buildSystemUpdate } from '@/config/data'

// Composables
const { notification, notificationType, showNotification } = useNotification()
const { activityLog, addActivity } = useActivityLog()
const { 
  loading, 
  results, 
  loadingClimate, 
  loadingDisease, 
  loadingGeoJSON,
  climateSuccess,
  diseaseSuccess,
  geojsonSuccess,
  forecastReportExists,
  lastJobId,
  triggerETL, 
  validateInputs, 
  checkForecastReportExists, 
  resetReports,
  fetchClimate,
  fetchDisease,
  fetchGeoJSON
} = useEtlPipeline()

// Page states
const showForecastModal = ref(false)
const showReportModal = ref(false)

// Config store
const forecastConfig = useForecastConfigStore()
const configIsValid = computed(() => forecastConfig.isValid)

// Factory for data import actions
const dataImportActions = buildDataImportActions({ loading, results })

// Factory for system update actions
const systemUpdateActions = buildSystemUpdate({ loading, results })

// Factory for pipeline steps
const pipelineSteps = buildPipelineSteps({
  configIsValid: configIsValid.value,
  loadingClimate: loadingClimate.value,
  loadingDisease: loadingDisease.value,
  loadingGeoJSON: loadingGeoJSON.value,
  loadingValidateInputs: loading.validate_inputs,
  climateSuccess: climateSuccess.value,
  diseaseSuccess: diseaseSuccess.value,
  geojsonSuccess: geojsonSuccess.value,
  validateInputsSuccess: results.validate_inputs,
  forecastReportExists: forecastReportExists.value,
  checkForecastReportExists,
  resetReports
})

const accordionItems = [
  { id: 'dataImport', title: 'Data Import' },
  { id: 'externalData', title: 'Upload External Data' },
  { id: 'forecastCreation', title: 'Forecast Creation' },
  { id: 'systemUpdate', title: 'System Update' }
]

const uploadFields = [
  { key: 'config', label: 'config.json', description: 'Forecast configuration (JSON)', accept: '.json,application/json' },
  { key: 'external_data', label: 'external_data.csv', description: 'External covariates (CSV)', accept: '.csv,text/csv' }
] as const

type UploadField = (typeof uploadFields)[number]

const uploadFiles = ref<Partial<Record<UploadField['key'], File>>>({})

const { uploading, deleting, serverFiles, refresh, upload, remove } = useInputUpload(addActivity)

const handleUpload = async (key: UploadField['key'], file: File) => {
  if (await upload(key, file)) uploadFiles.value[key] = undefined
}

const pendingDelete = ref<UploadField | null>(null)

const {
  current: previewCurrent,
  loading: previewLoading,
  error: previewError,
  config: previewConfig,
  csv: previewCsv,
  open: openPreview,
  close: closePreview
} = useInputPreview()

const fieldLabel = (key: UploadField['key']) => uploadFields.find(field => field.key === key)?.label ?? key

const confirmDelete = async () => {
  if (!pendingDelete.value) return
  await remove(pendingDelete.value.key)
  pendingDelete.value = null
}

const handleActionClick = async (key: string) => {
  if (key === 'navigate_to_forecast') {
    showForecastModal.value = true
    return
  }

  if (key === 'view_forecast_report') {
    showReportModal.value = true
    return
  }

  if (key.startsWith('fetch_')) {
    switch (key) {
      case 'fetch_climate':
        await fetchClimate()
        break
      case 'fetch_disease':
        await fetchDisease(forecastConfig)
        break
      case 'fetch_geojson':
        await fetchGeoJSON()
        break
    }
    return
  }

  if (key === 'validate_inputs') {
    await validateInputs(forecastConfig)
    return
  }

  await triggerETL(key)
}

const handleForecastJobCreated = (jobId: string) => {
  if (jobId) {
    lastJobId.value = jobId
    addActivity('Run Forecast', 'Forecast job started', true, jobId)
  }
}

const handleStepChange = (_stepIndex: number) => {
  // Step change tracking - can be extended for future needs
}

onMounted(() => {
  checkForecastReportExists()
  refresh()
})
</script>

<style scoped>
@reference "tailwindcss";

/* ===== Layout ===== */
.space-y-8 > * + * {
  margin-top: 2rem;
}

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
  display: flex;
  align-items: center;
  gap: 0.75rem;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.section-subtitle {
  color: #94a3b8;
  font-size: 0.875rem;
  margin-bottom: 2rem;
}

/* ===== Section Styles ===== */
.data-import-section,
.external-data-section,
.forecast-creation-section,
.system-update-section {
  margin-bottom: 2rem;
}

.data-import-title,
.forecast-creation-title,
.system-update-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* ===== External Data Upload ===== */
.upload-intro {
  color: #94a3b8;
  font-size: 0.875rem;
  margin-bottom: 1rem;
}

.upload-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

/* ===== Action Grid (shared with StepperCarousel) ===== */
.action-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.action-grid.gapless {
  grid-template-columns: repeat(2, 1fr);
  max-width: calc(66.666% + 1rem);
}

/* ===== Responsive ===== */
@media (max-width: 1024px) {
  .upload-grid {
    grid-template-columns: 1fr;
  }
  .action-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .action-grid.gapless {
    max-width: 100%;
  }
}

@media (max-width: 640px) {
  .action-grid {
    grid-template-columns: 1fr;
  }
  .action-grid.gapless {
    max-width: 100%;
  }
}
</style>
