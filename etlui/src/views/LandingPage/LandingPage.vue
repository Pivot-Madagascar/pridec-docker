<template>
  <div class="space-y-0">
    <!-- <HeroSection /> -->

    <section class="dashboard-section">
      <h2 class="section-header">ETL Pipeline</h2>
      <p class="section-subtitle">Follow the workflow step by step</p>

      <div class="data-import-section">
        <h3 class="data-import-title">Data Import</h3>
        <div class="action-grid" :class="{ gapless: dataImportActions.length <= 2 }">
          <ActionCard
            v-for="action in dataImportActions"
            :key="action.key"
            :action="action"
            @action-click="handleActionClick"
          />
        </div>
      </div>

      <StepperCarousel :steps="pipelineSteps" :initial-step="0" @action-click="handleActionClick" @step-change="handleStepChange">
        <template #step-1>
          <ForecastConfigForm />
        </template>
      </StepperCarousel>
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
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

import Notifications from './components/Notifications.vue'
import RecentActivity from './components/RecentActivity.vue'
import StepperCarousel from './components/StepperCarousel.vue'
import ForecastModal from './components/ForecastModal.vue'
import ForecastReportModal from './components/ForecastReportModal.vue'
import ForecastConfigForm from './components/ForecastConfigForm.vue'
import ActionCard from './components/ActionCard.vue'

import { useNotification } from '@/composables/useNotification'
import { useActivityLog } from '@/composables/useActivityLog'
import { useEtlPipeline } from '@/composables/useEtlPipeline'
import { useForecastConfigStore } from '@/stores/forecastConfig'
import { buildDataImportActions, buildPipelineSteps } from '@/config/data'

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
  resetReports,
  loading,
  results
})

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

/* ===== Data Import Section ===== */
.data-import-section {
  margin-bottom: 2rem;
}

.data-import-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
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
    grid-template-columns: 1fr;
  }
}
</style>