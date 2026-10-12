<template>
  <div class="forecast-runs">
    <!-- The 9 runs of the cycle: one couple source x disease each, one open at a time. -->
    <div class="runs-grid">
      <div v-for="couple in couples" :key="couple.name" class="run-chip" :class="`is-${couple.state}`">
        <span class="run-name">{{ couple.name }}</span>
        <span class="run-state">{{ couple.text }}</span>
      </div>
    </div>

    <!-- No run open: choose the couple to open. -->
    <div v-if="!run" class="run-open">
      <label class="field">
        <span class="field-label">Source</span>
        <select v-model="source" class="field-input">
          <option v-for="s in SOURCES" :key="s" :value="s">{{ s }}</option>
        </select>
      </label>
      <label class="field">
        <span class="field-label">Disease</span>
        <select v-model="disease" class="field-input">
          <option v-for="d in DISEASES" :key="d" :value="d">{{ d }}</option>
        </select>
      </label>
      <button type="button" class="btn btn-primary" :disabled="blocked || !forecastStep?.accessible" @click="emit('open', source, disease)">
        Open run {{ source }}/{{ disease }}
      </button>
      <p v-if="!forecastStep?.accessible" class="hint">Step 1 (data import) must be done first.</p>
      <p v-else class="hint">Opening a run empties input/ and output/, then restores the files already uploaded for this disease and level.</p>
    </div>

    <!-- The open run. -->
    <template v-else>
      <div class="run-header">
        <div>
          <h3 class="run-title">Run {{ run.couple }}</h3>
          <p class="run-context">
            DISEASE_CODE {{ run.disease_code }} · OU_LEVEL {{ run.ou_level }}<template v-if="run.alert_name"> · ALERT_NAME {{ run.alert_name }}</template>
          </p>
        </div>
        <button type="button" class="btn btn-danger" :disabled="blocked" @click="emit('abandon')">Abandon run</button>
      </div>

      <div class="run-files">
        <div>
          <p class="file-status">
            config.json for {{ diseaseOf(run.couple) }} (expected file: <code>{{ CONFIG_FILES[diseaseOf(run.couple)] }}</code>):
            <strong :class="`status-${configItem?.status ?? 'pending'}`">{{ configItem?.status ?? 'pending' }}</strong>
            (shared by the 3 runs of this disease)
          </p>
          <FileDropzone
            v-model="files.config"
            label="config.json"
            description="Forecast configuration of this disease (JSON)"
            accept=".json,application/json"
            :server-file="serverFiles.config"
            :uploading="busy"
            :deleting="busy"
            @upload="file => upload('config', file)"
            @delete="emit('delete', 'config')"
            @preview-local="file => emit('preview', 'config', file)"
            @preview-server="emit('preview', 'config', 'server')"
          />
        </div>
        <div>
          <p class="file-status">
            external_data.csv for the {{ levelOf(run.couple) }} level:
            <strong :class="`status-${externalItem?.status ?? 'pending'}`">{{ externalItem?.status ?? 'pending' }}</strong>
            (shared by the runs of this level)
          </p>
          <FileDropzone
            v-model="files.external_data"
            label="external_data.csv"
            description="External covariates of this org unit level (CSV)"
            accept=".csv,text/csv"
            :server-file="serverFiles.external_data"
            :uploading="busy"
            :deleting="busy"
            @upload="file => upload('external_data', file)"
            @delete="emit('delete', 'external_data')"
            @preview-local="file => emit('preview', 'external_data', file)"
            @preview-server="emit('preview', 'external_data', 'server')"
          />
        </div>
      </div>

      <div class="action-grid">
        <ActionCard v-for="card in jobCards" :key="card.key" :action="card" @action-click="emit('launch', $event)" />
      </div>

      <div class="run-approval">
        <span class="file-status">
          Approval: <strong :class="`status-${approveItem?.status ?? 'pending'}`">{{ approveItem?.status ?? 'pending' }}</strong>
        </span>
        <button type="button" class="btn" @click="emit('view-report')">View report</button>
        <button type="button" class="btn btn-primary" :disabled="blocked || !approveItem?.launchable" @click="emit('decide', 'approve')">Approve</button>
        <button type="button" class="btn btn-danger" :disabled="blocked || forecastItem?.status !== 'success'" @click="emit('decide', 'reject')">Reject</button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import ActionCard from '@/views/Dashboard/components/ActionCard.vue'
import FileDropzone from '@/views/Dashboard/components/FileDropzone.vue'
import { CONFIG_FILES, step, toCard } from '@/config/pipeline'
import { DISEASES, SOURCES, type Checkpoints, type Disease, type Source } from '@/types/pipeline'
import type { InputName, ServerFile } from '@/types/inputs'

const props = defineProps<{
  state: Checkpoints | null
  serverFiles: Partial<Record<InputName, ServerFile>>
  busy: boolean
  // Returns true once uploaded: the selected file is then cleared.
  uploadFile: (name: InputName, file: File) => Promise<boolean>
}>()

const emit = defineEmits<{
  open: [source: Source, disease: Disease]
  abandon: []
  launch: [item: string]
  decide: [decision: 'approve' | 'reject']
  delete: [name: InputName]
  preview: [name: InputName, from: File | 'server']
  'view-report': []
}>()

const source = ref<Source>('ADJ')
const disease = ref<Disease>('Malaria')
const files = reactive<Partial<Record<InputName, File>>>({})

const diseaseOf = (couple: string) => couple.split('/')[1]
const levelOf = (couple: string) => (couple.startsWith('CSB/') ? 'CSB' : 'fokontany')

const forecastStep = computed(() => step(props.state, 'forecast'))
const run = computed(() => props.state?.run ?? null)
const blocked = computed(() => props.busy || props.state?.lock != null)
const itemOf = (name: string) => forecastStep.value?.items.find(i => i.item === name)
const configItem = computed(() => run.value && itemOf(`config/${diseaseOf(run.value.couple)}`))
const externalItem = computed(() => run.value && itemOf(`external_data/${run.value.couple.startsWith('CSB/') ? 'csb' : 'fkt'}`))
const approveItem = computed(() => run.value && itemOf(`${run.value.couple}:approve`))
const forecastItem = computed(() => run.value && itemOf(`${run.value.couple}:forecast`))

// The run's jobs, as cards (the uploads and approve have their own controls above and below).
const jobCards = computed(() =>
  (forecastStep.value?.items ?? [])
    .filter(i => run.value && i.item.startsWith(`${run.value.couple}:`) && !i.item.endsWith(':approve'))
    .map(i => toCard(i, props.state, props.busy))
)

const couples = computed(() =>
  SOURCES.flatMap(s =>
    DISEASES.map(d => {
      const name = `${s}/${d}`
      const items = (forecastStep.value?.items ?? []).filter(i => i.item.startsWith(`${name}:`))
      const done = items.filter(i => i.status === 'success').length
      if (items.find(i => i.item.endsWith(':post_forecast'))?.status === 'success') return { name, state: 'done', text: '✓ Published' }
      if (run.value?.couple === name) return { name, state: 'open', text: `Open · ${done}/${items.length}` }
      return { name, state: 'idle', text: `${done}/${items.length}` }
    })
  )
)

async function upload(name: InputName, file: File) {
  if (await props.uploadFile(name, file)) files[name] = undefined
}
</script>

<style scoped>
@reference "tailwindcss";

.forecast-runs {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.runs-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
}

.run-chip {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 0.8125rem;
}

.run-chip.is-open {
  border-color: #6366f1;
}

.run-chip.is-done {
  border-color: #10b981;
}

.run-name {
  font-weight: 600;
  color: #f1f5f9;
}

.run-state {
  color: #94a3b8;
}

.run-open,
.run-approval {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.field-label {
  font-size: 0.75rem;
  color: #94a3b8;
}

.field-input {
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  background: #0f172a;
  color: #f1f5f9;
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.hint {
  width: 100%;
  font-size: 0.8125rem;
  color: #94a3b8;
}

.run-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.run-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #f1f5f9;
}

.run-context,
.file-status {
  font-size: 0.8125rem;
  color: #94a3b8;
  margin-bottom: 0.5rem;
}

.run-files {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.status-success {
  color: #34d399;
}

.status-error {
  color: #f87171;
}

.status-running {
  color: #fbbf24;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  cursor: pointer;
}

.btn-primary {
  background: #4f46e5;
  border-color: #4f46e5;
  color: #fff;
}

.btn-danger {
  background: rgba(220, 38, 38, 0.2);
  border-color: rgba(220, 38, 38, 0.6);
  color: #fca5a5;
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

@media (max-width: 1024px) {
  .runs-grid,
  .run-files,
  .action-grid {
    grid-template-columns: 1fr;
  }
}
</style>
