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
    <Progress :model-value="done" :max="inputs.length + items.length" />
    <p class="level-progress">
      {{ done }} of {{ inputs.length + items.length }} steps
      <span v-if="isOpen" class="card-steps-hint">Click to see the steps</span>
    </p>

    <Dialog v-if="isOpen" :open="showSteps" @update:open="showSteps = $event">
      <DialogContent class="flex max-h-[90vh] w-[min(96vw,1600px)] max-w-none flex-col sm:max-w-none" data-test="steps-dialog" :aria-describedby="undefined">
      <!-- ponytail: ForecastRuns' global CSS is namespaced `.forecast-runs .steps-dialog`; the portal leaves that tree, so
           these wrappers restore it. They go when ForecastRuns gets restyled (tailwind-migration phase 6). -->
      <div class="forecast-runs min-h-0 overflow-y-auto"><div class="steps-dialog">
      <header class="steps-header pr-10">
        <DialogTitle as="h5" class="level-title">{{ LEVEL_NAMES[source] }} <span class="level-code">{{ source }}</span> · {{ disease }}</DialogTitle>
        <!-- Stops this run only (the pass goes on): its items go back to "To do", the run can be opened again later. -->
        <Button variant="destructive" size="sm" data-test="abandon-run" :disabled="blocked" @click="emit('abandon')">Abandon this run</Button>
      </header>
      <!-- Four columns side by side, each headed by its step of the stepper, green once all its items succeed. -->
      <ol class="steps-columns">
        <li v-for="(column, n) in columns" :key="column.title" class="steps-column" data-test="steps-column" :aria-label="column.title">
        <p class="step" :class="{ 'is-done': column.done }" data-test="step">
          <span class="step-mark" aria-hidden="true">{{ column.done ? '✓' : n + 1 }}</span>
          <span class="step-title">{{ column.title }}<span v-if="column.done" class="sr-only"> (done)</span></span>
        </p>
        <ol class="item-list">
          <!-- The run's input files: etlhub keeps one per disease (config) and one per level (external_data), shared by those runs. -->
          <li v-for="input in column.inputs" :key="input.item" class="item item-input" data-test="item" :data-item="input.item" :class="`item-${input.status}`">
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
          <li v-for="row in column.rows" :key="row.item" class="item" :class="[`item-${row.look}`, `job-${row.job}`]" data-test="item" :data-job="row.job" :data-item="row.item">
            <span class="item-dot" aria-hidden="true"></span>
            <span class="item-text">
              <span class="item-label">{{ row.label }}</span>
              <code class="item-tech" data-test="item-tech">{{ row.job }}</code>
              <span class="item-state">{{ LOOK_TEXT[row.look] }}</span>
              <span v-if="row.updated" class="item-state item-time" data-test="item-time">{{ row.updated }}</span>
            </span>
            <Button
              v-if="row.launch"
              variant="outline"
              size="sm"
              :disabled="blocked"
              :aria-label="`${row.launch} : ${row.label}`"
              @click="emit('launch', row.item)"
            >
              {{ row.launch }}
            </Button>
            <Button v-if="row.skip" variant="ghost" size="sm" :disabled="blocked" data-test="skip-alerts"
              :aria-label="`Skip : ${row.label}`" @click="emit('skip')">
              Skip
            </Button>
            <!-- The approval is a decision: read the forecast report, then approve or reject it there. -->
            <Button v-else-if="row.look === 'waiting'" size="sm" :disabled="blocked" @click="emit('validate')">
              Read and approve
            </Button>
          </li>
          <!-- The data check, after the 3 fetches, in the same look as them; it closes the data preparation. -->
          <li v-if="column.check" class="item" :class="`item-${column.check.look}`" data-test="data-check" :data-item="column.check.item">
            <span class="item-dot" aria-hidden="true"></span>
            <span class="item-text">
              <span class="item-label">{{ column.check.label }}</span>
              <code class="item-tech" data-test="item-tech">{{ column.check.job }}</code>
              <span class="item-state">
                {{ column.check.look === 'pending' && !column.check.launch ? 'Available once the input files and the 3 fetches are done' : LOOK_TEXT[column.check.look] }}
              </span>
              <span v-if="column.check.updated" class="item-state item-time" data-test="item-time">{{ column.check.updated }}</span>
            </span>
            <Button v-if="column.check.launch" variant="outline" size="sm" :disabled="blocked"
              :aria-label="`${column.check.launch} : ${column.check.label}`" @click="emit('launch', column.check.item)">
              {{ column.check.launch }}
            </Button>
          </li>
        </ol>
        <!-- After the data check: what input/ holds, i.e. what the forecast computation will read. Not an item: no state. -->
        <div v-if="column.check" class="input-archive" data-test="input-archive">
          <span class="item-text">
            <span class="item-label">Input files</span>
            <span class="item-state">The files the forecast computation will use, as a zip</span>
          </span>
          <Button as="a" variant="outline" :href="runs.inputArchiveUrl" target="_blank" rel="noopener" download>
            <Download aria-hidden="true" /> Download the input files
          </Button>
        </div>
        </li>
      </ol>
      </div></div>
      </DialogContent>
    </Dialog>

    <div class="level-action">
      <Button v-if="status.key === 'published'" variant="outline" class="w-full" @click="emit('report', source, disease)">View report</Button>
      <Button v-else-if="status.key === 'waiting'" class="w-full" :disabled="blocked" @click="emit('validate')">
        Read and approve
      </Button>
      <template v-else-if="!isOpen">
        <p v-if="runs.state?.run" class="hint">Available once the open run is done</p>
        <Button v-else class="w-full" :disabled="blocked || !accessible" @click="emit('open', source, disease)">Open</Button>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, inject, reactive, ref, useId, watch } from 'vue'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { Download } from '@lucide/vue'
import FileDropzone from '@/views/Dashboard/components/FileDropzone.vue'
import { CONFIG_FILES, DISEASE_NAMES, FILE_STATUS, ITEM_NAMES, LEVEL_NAMES, jobOf, lastUpdate, step } from '@/config/pipeline'
import { pointTo } from '@/utils/attention'
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
      launch: !launchable ? null : i.status === 'pending' ? 'Launch' : 'Relaunch',
      // The CSB alerts can also be marked done without computing them (POST /pipeline/runs/current/skip_alerts).
      skip: launchable && job === 'calc_orgunit_alerts' && i.status !== 'success'
    }
  })
)

// The 4 columns: input files | the 3 fetches and the data check | forecast (CSB alerts) and approval | publication.
// A column is done when all its items succeed (none loaded yet: not done).
type Row = (typeof rows.value)[number]
const PREPARE = ['fetch_disease', 'fetch_climate', 'fetch_geojson']
function column(title: string, columnInputs: typeof inputs.value, columnRows: Row[], check?: Row) {
  const states = [...columnInputs.map(i => i.status), ...[...columnRows, ...(check ? [check] : [])].map(r => r.look)]
  return { title, inputs: columnInputs, rows: columnRows, check, done: states.length > 0 && states.every(s => s === 'success') }
}
const columns = computed(() => {
  const jobs = (keep: (job: string) => boolean) => rows.value.filter(r => keep(r.job))
  return [
    column('Input files', inputs.value, []),
    column('Prepare the data', [], jobs(j => PREPARE.includes(j)), rows.value.find(r => r.job === 'validate_inputs')),
    column('Forecast and approval', [], jobs(j => ![...PREPARE, 'validate_inputs', 'post_forecast'].includes(j))),
    column('Publication', [], jobs(j => j === 'post_forecast'))
  ]
})

// The breadcrumb's "go to the current item" (Dashboard): the open run opens its steps and points to it.
watch(() => runs.focus, focus => {
  if (!focus || !isOpen.value) return
  showSteps.value = true
  pointTo(`[data-test="steps-dialog"] [data-item="${focus.item}"]`, focus.blink)
})
</script>
