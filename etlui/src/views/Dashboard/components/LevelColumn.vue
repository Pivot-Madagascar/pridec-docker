<template>
  <!-- One run (level x disease): its status and a progress bar. Once the run is open, the whole card opens the
       "Steps" dialog: its input files, every item and its launch button. -->
  <section class="level-column" :class="{ 'is-open': isOpen }" data-test="level-column" :aria-current="isOpen ? 'true' : undefined" :aria-labelledby="titleId">
    <!-- Covers the card; the actions below sit above it (.level-action). -->
    <button
      v-if="isOpen"
      type="button"
      class="card-steps" data-test="card-steps"
      :aria-label="`Steps of ${LEVEL_NAMES[source]} · ${disease}`"
      @click="showSteps = true"
    ></button>
    <h5 :id="titleId" class="level-title">{{ LEVEL_NAMES[source] }} <span class="level-code">{{ source }}</span></h5>
    <p class="level-status" :class="`status-${status.key}`">{{ status.text }}</p>
    <progress class="level-bar" :value="done" :max="inputs.length + items.length"></progress>
    <p class="level-progress">
      {{ done }} of {{ inputs.length + items.length }} steps
      <span v-if="isOpen" class="card-steps-hint">Click to see the steps</span>
    </p>

    <BaseDialog v-if="isOpen" :open="showSteps" backdrop-close class="steps-dialog" :aria-label="`${LEVEL_NAMES[source]} · ${disease}`" @dismiss="showSteps = false">
      <header class="steps-header">
        <h5 class="level-title">{{ LEVEL_NAMES[source] }} <span class="level-code">{{ source }}</span> · {{ disease }}</h5>
        <button type="button" class="steps-close" data-test="steps-close" aria-label="Close the steps" @click="showSteps = false">
          <Icon :path="ICONS.close" class="steps-close-icon" />
        </button>
      </header>
      <!-- Two stages: preparing the data, then the forecast. Stage 2 opens once the data check succeeds (Next / Previous). -->
      <section v-for="tile in tiles" v-show="shown === tile.n" :key="tile.n" class="steps-tile" data-test="steps-tile" :aria-label="tile.title">
        <ol class="item-list">
          <!-- The run's input files: etlhub keeps one per disease (config) and one per level (external_data), shared by those runs. -->
          <li v-for="input in tile.n === 1 ? inputs : []" :key="input.item" class="item item-input" data-test="item" :class="`item-${input.status}`">
            <span class="item-dot" aria-hidden="true"></span>
            <span class="item-text">
              <span class="item-label">{{ input.label }}</span>
              <code class="item-tech" data-test="item-tech">{{ input.item }}</code>
              <span class="item-state">{{ FILE_STATUS[input.status] }} · {{ input.shared }}</span>
            </span>
            <FileDropzone
              v-model="files[input.name]"
              class="item-file"
              :label="input.file"
              :description="input.description"
              :accept="input.accept"
              :server-file="runs.serverFiles[input.name]"
              :default-file="runs.defaults[input.item]"
              :disabled="!input.launchable"
              :busy="runs.busy"
              @upload="f => upload(input.name, f)"
              @delete="emit('delete', input.name)"
              @preview-local="f => emit('preview', input.name, f)"
              @preview-server="emit('preview', input.name, 'server')"
              @preview-default="emit('preview', input.name, { default: input.item })"
              @use-default="emit('use-default', input.name)"
            />
          </li>
          <li v-for="row in tile.rows" :key="row.item" class="item" :class="[`item-${row.look}`, `job-${row.job}`]" data-test="item" :data-job="row.job">
            <span class="item-dot" aria-hidden="true"></span>
            <span class="item-text">
              <span class="item-label">{{ row.label }}</span>
              <code class="item-tech" data-test="item-tech">{{ row.job }}</code>
              <span class="item-state">{{ LOOK_TEXT[row.look] }}</span>
              <span v-if="row.updated" class="item-state item-time" data-test="item-time">{{ row.updated }}</span>
            </span>
            <button
              v-if="row.launch"
              type="button"
              class="btn btn-small"
              :disabled="blocked"
              :aria-label="`${row.launch} : ${row.label}`"
              @click="emit('launch', row.item)"
            >
              {{ row.launch }}
            </button>
            <!-- The approval is a decision: read the forecast report, then approve or reject it there. -->
            <button
              v-else-if="row.look === 'waiting'"
              type="button"
              class="btn btn-small btn-primary"
              :disabled="blocked"
              @click="emit('validate')"
            >
              Read and approve
            </button>
          </li>
        </ol>
        <!-- The data check is a button, not a card: it closes stage 1. -->
        <div v-if="tile.n === 1 && check" class="data-check" data-test="data-check" :class="`item-${check.look}`">
          <span class="item-text">
            <span class="item-label">{{ check.label }}</span>
            <span class="item-state">
              {{ check.look === 'pending' && !check.launch ? 'Available once the 5 items above are done' : LOOK_TEXT[check.look] }}
            </span>
          </span>
          <button type="button" class="btn btn-primary" :disabled="blocked || !check.launch" @click="emit('launch', check.item)">
            {{ check.look === 'pending' ? 'Run the data check' : 'Relaunch the data check' }}
          </button>
          <button type="button" class="btn" :disabled="!checked" @click="shown = 2">Next →</button>
        </div>
        <div v-if="tile.n === 2" class="tile-nav" data-test="tile-nav">
          <button type="button" class="btn" @click="shown = 1">← Previous</button>
        </div>
      </section>
    </BaseDialog>

    <div class="level-action">
      <button v-if="status.key === 'published'" type="button" class="btn" @click="emit('report', source, disease)">View report</button>
      <button v-else-if="status.key === 'waiting'" type="button" class="btn btn-primary" :disabled="blocked" @click="emit('validate')">
        Read and approve
      </button>
      <template v-else-if="!isOpen">
        <p v-if="runs.state?.run" class="hint">Available once the open run is done</p>
        <button v-else type="button" class="btn btn-primary" :disabled="blocked || !accessible" @click="emit('open', source, disease)">Open</button>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, inject, reactive, ref, useId, watch } from 'vue'
import BaseDialog from './BaseDialog.vue'
import Icon, { ICONS } from '@/components/Icons'
import FileDropzone from '@/views/Dashboard/components/FileDropzone.vue'
import { CONFIG_FILES, DISEASE_NAMES, FILE_STATUS, ITEM_NAMES, LEVEL_NAMES, jobOf, lastUpdate, step } from '@/config/pipeline'
import type { Disease, PipelineItem, Source } from '@/types/pipeline'
import type { InputName } from '@/types/inputs'
import { RUNS } from './runs'

const props = defineProps<{ source: Source; disease: Disease }>()
const { props: runs, emit } = inject(RUNS)!

type Look = 'success' | 'waiting' | 'running' | 'error' | 'pending'
// Never the colour alone: every state also has its text.
const LOOK_TEXT: Record<Look, string> = {
  success: '✓ Done',
  waiting: '⏳ Waiting for your decision',
  running: '⟳ Running…',
  error: '✗ Failed: relaunch this step',
  pending: 'To do'
}

const titleId = useId()
const showSteps = ref(false)
const couple = computed(() => `${props.source}/${props.disease}`)
const items = computed<PipelineItem[]>(() =>
  (step(runs.state, 'forecast')?.items ?? []).filter(i => i.item.startsWith(`${couple.value}:`))
)
const accessible = computed(() => step(runs.state, 'forecast')?.accessible ?? false)
const isOpen = computed(() => runs.state?.run?.couple === couple.value)
const blocked = computed(() => runs.busy || runs.state?.lock != null)
const files = reactive<Partial<Record<InputName, File>>>({})
const itemOf = (name: string) => step(runs.state, 'forecast')?.items.find(i => i.item === name)

// config/<disease> and external_data/<fkt|csb>: the same items as the other runs of that disease or level.
const inputs = computed(() => {
  const level = props.source === 'CSB' ? 'csb' : 'fkt'
  const levelName = props.source === 'CSB' ? 'health centre' : 'fokontany'
  return [
    { name: 'config' as const, item: `config/${props.disease}`, label: `Parameters (${CONFIG_FILES[props.disease]})`,
      file: 'config.json', accept: '.json,application/json', description: 'Forecast parameters of this disease (JSON)',
      shared: `same file for the 3 ${DISEASE_NAMES[props.disease]} runs` },
    { name: 'external_data' as const, item: `external_data/${level}`, label: 'External data',
      file: 'external_data.csv', accept: '.csv,text/csv', description: `External covariates of the ${levelName}s (CSV)`,
      shared: `same file for every ${levelName} run` }
  ].map(input => {
    const item = itemOf(input.item)
    return { ...input, status: item?.status ?? 'pending', launchable: !!item?.launchable }
  })
})

async function upload(name: InputName, selected: File) {
  if (await runs.uploadFile(name, selected)) files[name] = undefined
}

const done = computed(() =>
  [...inputs.value, ...items.value].filter(i => i.status === 'success').length
)
const byJob = (job: string) => items.value.find(i => jobOf(i.item) === job)
const awaiting = (i: PipelineItem) => isOpen.value && jobOf(i.item) === 'approve' && i.status === 'pending' && i.launchable

const status = computed(() => {
  if (byJob('post_forecast')?.status === 'success') return { key: 'published', text: '✓ Published' }
  const approve = byJob('approve')
  if (approve && awaiting(approve)) return { key: 'waiting', text: '⏳ To approve' }
  if (isOpen.value) return { key: 'open', text: '● In progress' }
  return { key: 'idle', text: 'Not started yet' }
})

// The open run's jobs get a button when etlhub says they can start (approve goes through "Read and approve").
const rows = computed(() =>
  items.value.map(i => {
    const job = jobOf(i.item)
    const look: Look = awaiting(i) ? 'waiting' : i.status
    const launchable = job !== 'approve' && i.launchable && i.status !== 'running'
    return {
      item: i.item, job, look,
      label: ITEM_NAMES[job] ?? job,
      updated: lastUpdate(i),
      // ponytail: calc_orgunit_alerts has no script yet (501), so its button skips it; back to Launch once it exists.
      launch: !launchable ? null : job === 'calc_orgunit_alerts' ? 'Skip' : i.status === 'pending' ? 'Launch' : 'Relaunch'
    }
  })
)

// Stage 1: input files, the 3 fetches and the data check; stage 2: everything after it.
const PREPARE = ['fetch_disease', 'fetch_climate', 'fetch_geojson']
const check = computed(() => rows.value.find(r => r.job === 'validate_inputs'))
const checked = computed(() => check.value?.look === 'success')
const tiles = computed(() => [
  { n: 1, title: 'Prepare the data', rows: rows.value.filter(r => PREPARE.includes(r.job)) },
  { n: 2, title: 'Forecast and publish', rows: rows.value.filter(r => !PREPARE.includes(r.job) && r.job !== 'validate_inputs') }
])
// Follows the data check: stage 2 once it succeeds, back to stage 1 if it is reset (a new input file).
const shown = ref(1)
watch(checked, ok => { shown.value = ok ? 2 : 1 }, { immediate: true })
</script>
