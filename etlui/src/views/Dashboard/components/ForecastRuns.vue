<template>
  <div class="forecast-runs">
    <p class="todo" role="status"><strong>To do now:</strong> {{ todo }}</p>

    <!-- One external_data.csv per level, shared by the 3 diseases: etlhub takes it only while a run of that level is open. -->
    <section class="external-data" aria-labelledby="external-data-title">
      <h4 id="external-data-title" class="section-title">External data</h4>
      <div class="input-grid">
        <div v-for="level in EXTERNAL_LEVELS" :key="level.key" class="input-file">
          <p class="hint">
            {{ level.name }}:
            <strong :class="itemOf(level.key)?.status === 'success' ? 'text-success' : 'text-todo'">
              {{ FILE_STATUS[itemOf(level.key)?.status ?? 'pending'] }}
            </strong>
            <template v-if="!itemOf(level.key)?.launchable"> · can be changed while a {{ level.runs }} run is open</template>
          </p>
          <FileDropzone
            v-model="files[level.key]"
            label="external_data.csv"
            :description="`External covariates of the ${level.name.toLowerCase()} (CSV)`"
            accept=".csv,text/csv"
            :server-file="openLevel === level.key ? serverFiles.external_data : undefined"
            :disabled="!itemOf(level.key)?.launchable"
            :uploading="busy"
            :deleting="busy"
            @upload="file => upload(level.key, file)"
            @delete="emit('delete', 'external_data')"
            @preview-local="file => emit('preview', 'external_data', file)"
            @preview-server="emit('preview', 'external_data', 'server')"
          />
        </div>
      </div>
    </section>

    <!-- The carousel has no scrollbar: these buttons (and each card's "Next disease") move between diseases. -->
    <nav class="disease-nav" aria-label="Diseases">
      <a
        v-for="(disease, i) in DISEASES"
        :key="disease"
        class="btn btn-small"
        :class="{ 'is-active': i === shown }"
        :aria-current="i === shown ? 'true' : undefined"
        :href="`#forecast-${disease}`"
      >
        {{ DISEASE_NAMES[disease] }}
      </a>
    </nav>
    <div class="carousel" tabindex="0" aria-label="Forecasts by disease" @scroll="onScroll">
      <DiseaseCard
        v-for="(disease, i) in DISEASES"
        :id="`forecast-${disease}`"
        :key="disease"
        :disease="disease"
        :next="DISEASES[(i + 1) % DISEASES.length]"
        :state="state"
        :busy="busy"
        :server-files="serverFiles"
        :upload-file="uploadFile"
        @open="(source, d) => emit('open', source, d)"
        @launch="item => emit('launch', item)"
        @validate="emit('validate')"
        @report="(source, d) => emit('report', source, d)"
        @delete="name => emit('delete', name)"
        @preview="(name, from) => emit('preview', name, from)"
      />
    </div>

    <details v-if="isAdmin" class="admin-zone">
      <summary>Administration</summary>
      <div class="admin-actions">
        <button type="button" class="btn btn-danger" :disabled="busy || !state?.lock" @click="emit('release')">Release the lock</button>
        <button type="button" class="btn btn-danger" :disabled="busy || !!state?.lock || !state?.run" @click="emit('abandon')">
          Abandon the open forecast run
        </button>
      </div>
    </details>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import DiseaseCard from '@/views/Dashboard/components/DiseaseCard.vue'
import FileDropzone from '@/views/Dashboard/components/FileDropzone.vue'
import { DISEASE_NAMES, FILE_STATUS, ITEM_NAMES, coupleName, jobOf, labelOf, step } from '@/config/pipeline'
import { DISEASES, type Checkpoints, type Disease, type Source } from '@/types/pipeline'
import type { InputName, ServerFile } from '@/types/inputs'

const props = defineProps<{
  state: Checkpoints | null
  busy: boolean
  isAdmin: boolean
  serverFiles: Partial<Record<InputName, ServerFile>>
  uploadFile: (name: InputName, file: File) => Promise<boolean>
}>()

const emit = defineEmits<{
  open: [source: Source, disease: Disease]
  launch: [item: string]
  validate: []
  report: [source: Source, disease: Disease]
  delete: [name: InputName]
  preview: [name: InputName, from: File | 'server']
  abandon: []
  release: []
}>()

const EXTERNAL_LEVELS = [
  { key: 'external_data/fkt', name: 'Fokontany', runs: 'ADJ or COM' },
  { key: 'external_data/csb', name: 'Health centres', runs: 'CSB' }
]
const files = reactive<Record<string, File | undefined>>({})

// Index of the disease card on screen: each card is 100% of the carousel width.
const shown = ref(0)
const onScroll = (e: Event) => {
  const el = e.target as HTMLElement
  shown.value = Math.round(el.scrollLeft / el.clientWidth)
}

// input/ holds the open run's files: the server file belongs to the open run's level only.
const openLevel = computed(() => {
  const couple = props.state?.run?.couple
  return couple ? `external_data/${couple.startsWith('CSB/') ? 'csb' : 'fkt'}` : null
})

async function upload(key: string, file: File) {
  if (await props.uploadFile('external_data', file)) files[key] = undefined
}

const forecastStep = computed(() => step(props.state, 'forecast'))
const itemOf = (name: string) => forecastStep.value?.items.find(i => i.item === name)

// The next human action, read from the open run and what etlhub says can start.
const todo = computed(() => {
  const state = props.state
  if (!state) return 'loading…'
  if (state.lock) return `wait, “${ITEM_NAMES[state.lock.task] ?? labelOf(state.lock.task)}” is running.`
  if (!forecastStep.value?.accessible) return 'finish step 1 (data import) first.'
  const run = state.run
  if (!run) {
    const left = forecastStep.value.items.some(i => i.item.endsWith(':post_forecast') && i.status !== 'success')
    return left ? 'open a forecast run below.' : "all of this month's forecasts are published."
  }
  const name = coupleName(run.couple)
  const disease = run.couple.split('/')[1]
  const next = forecastStep.value.items.find(i =>
    i.launchable && i.status !== 'success' &&
      (i.item.startsWith(`${run.couple}:`) || i.item === `config/${disease}` || i.item === openLevel.value)
  )
  if (!next) return `nothing to launch for ${name}.`
  if (next.item.startsWith('config/')) return `provide the parameters of ${name}.`
  if (next.item.startsWith('external_data/')) return `provide the external data of ${name}.`
  const job = jobOf(next.item)
  return job === 'approve' ? `approve ${name}.` : `launch “${ITEM_NAMES[job] ?? job}” for ${name}.`
})
</script>

<style>
/* Step ② only: not scoped, so DiseaseCard and LevelColumn share it. */
.forecast-runs {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  color: #e2e8f0;
}

.forecast-runs .hint {
  font-size: 0.8125rem;
  color: #94a3b8;
}

.forecast-runs .todo {
  padding: 1rem 1.25rem;
  border-radius: 0.75rem;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.45);
  color: #fde68a;
}

.forecast-runs .disease-nav,
.forecast-runs .admin-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.forecast-runs .btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.15);
  cursor: pointer;
  text-decoration: none;
}

.forecast-runs .btn:focus-visible,
.forecast-runs .carousel:focus-visible,
.forecast-runs a:focus-visible,
.forecast-runs summary:focus-visible {
  outline: 2px solid #818cf8;
  outline-offset: 2px;
}

.forecast-runs .btn-primary {
  background: #4f46e5;
  border-color: #4f46e5;
  color: #fff;
}

.forecast-runs .btn-danger {
  background: rgba(220, 38, 38, 0.2);
  border-color: rgba(220, 38, 38, 0.6);
  color: #fca5a5;
}

.forecast-runs .btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.forecast-runs .carousel {
  display: flex;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  scroll-behavior: smooth;
  scrollbar-width: none;
  border-radius: 1rem;
}

.forecast-runs .carousel::-webkit-scrollbar {
  display: none;
}

.forecast-runs .disease-card {
  flex: 0 0 100%;
  scroll-snap-align: start;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 2.5rem;
  border-radius: 1rem;
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.forecast-runs .card-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: baseline;
  gap: 1rem;
}

.forecast-runs .card-title {
  font-size: 1.375rem;
  font-weight: 700;
  color: #f1f5f9;
}

.forecast-runs .card-progress {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: #cbd5e1;
}

.forecast-runs .progress-dots {
  display: flex;
  gap: 0.375rem;
}

.forecast-runs .progress-dot {
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 9999px;
  border: 2px solid #475569;
}

.forecast-runs .progress-dot.is-done {
  background: #10b981;
  border-color: #10b981;
}

.forecast-runs .input-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
}

.forecast-runs .input-file .hint {
  margin-bottom: 0.5rem;
}

.forecast-runs code {
  font-size: 0.75rem;
  color: #94a3b8;
}

.forecast-runs .level-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
}

.forecast-runs .level-column {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.25rem;
  border-radius: 0.75rem;
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.forecast-runs .level-column.is-open {
  border-color: #6366f1;
}

.forecast-runs .level-title {
  font-size: 1rem;
  font-weight: 700;
  color: #f1f5f9;
}

.forecast-runs .level-code {
  font-size: 0.75rem;
  color: #94a3b8;
}

.forecast-runs .level-status {
  font-weight: 600;
}

.forecast-runs .status-published,
.forecast-runs .text-success {
  color: #34d399;
}

.forecast-runs .status-waiting,
.forecast-runs .text-todo {
  color: #fbbf24;
}

.forecast-runs .status-open {
  color: #a5b4fc;
}

.forecast-runs .status-idle {
  color: #94a3b8;
  font-size: 0.875rem;
}

.forecast-runs .level-progress {
  color: #94a3b8;
  font-size: 0.875rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.forecast-runs .level-bar {
  width: 100%;
  height: 0.5rem;
  accent-color: #10b981;
}

.forecast-runs .steps-dialog {
  width: min(32rem, calc(100vw - 2rem));
}

.forecast-runs .item-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin: 1rem 0;
}

.forecast-runs .item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 0.75rem;
}

.forecast-runs .item-dot {
  width: 0.875rem;
  height: 0.875rem;
  border-radius: 9999px;
  background: #475569;
}

.forecast-runs .item-text {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.forecast-runs .item-label {
  font-size: 0.9375rem;
  color: #f1f5f9;
}

.forecast-runs .item-tech {
  font-size: 0.6875rem;
}

.forecast-runs .item-state {
  font-size: 0.75rem;
  color: #94a3b8;
}

.forecast-runs .item-pending .item-label {
  color: #94a3b8;
}

.forecast-runs .item-success .item-dot {
  background: #10b981;
}

.forecast-runs .item-waiting .item-dot {
  background: #f59e0b;
  box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.3);
}

.forecast-runs .item-waiting .item-state {
  color: #fbbf24;
}

.forecast-runs .item-running .item-dot {
  background: transparent;
  border: 2px solid #818cf8;
  border-top-color: transparent;
  animation: forecast-spin 0.8s linear infinite;
}

.forecast-runs .item-running .item-state {
  color: #a5b4fc;
}

.forecast-runs .item-error .item-dot {
  background: #ef4444;
}

.forecast-runs .item-error .item-state {
  color: #f87171;
}

.forecast-runs .disease-nav .is-active {
  background: #4f46e5;
  border-color: #4f46e5;
  color: #fff;
}

.forecast-runs .btn-small {
  padding: 0.25rem 0.75rem;
  font-size: 0.8125rem;
}

.forecast-runs .level-action {
  margin-top: auto;
}

.forecast-runs .level-action .btn {
  width: 100%;
}

.forecast-runs .next-link {
  align-self: flex-end;
  color: #a5b4fc;
  font-weight: 600;
  padding: 0.75rem 0;
}

.forecast-runs .section-title {
  font-size: 1rem;
  font-weight: 700;
  color: #f1f5f9;
  margin-bottom: 0.75rem;
}

.forecast-runs .admin-zone summary {
  cursor: pointer;
  min-height: 44px;
  display: flex;
  align-items: center;
  color: #94a3b8;
  font-weight: 600;
}

.forecast-runs .admin-actions {
  padding-top: 0.75rem;
}

@keyframes forecast-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .forecast-runs .item-running .item-dot {
    animation: none;
  }

  .forecast-runs .carousel {
    scroll-behavior: auto;
  }
}

@media (max-width: 820px) {
  .forecast-runs .level-grid,
  .forecast-runs .input-grid {
    grid-template-columns: 1fr;
  }

  .forecast-runs .disease-card {
    padding: 1.5rem;
  }
}
</style>
