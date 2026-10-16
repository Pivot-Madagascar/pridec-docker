<template>
  <!-- One disease: its shared config.json and its 3 runs (ADJ, COM, CSB) side by side. -->
  <article class="disease-card" :aria-labelledby="titleId">
    <header class="card-header">
      <h4 :id="titleId" class="card-title">{{ DISEASE_NAMES[disease] }}</h4>
      <p class="card-progress">
        {{ published.length }} of 3 levels published
        <span class="progress-dots" aria-hidden="true">
          <span v-for="source in SOURCES" :key="source" class="progress-dot" :class="{ 'is-done': published.includes(source) }"></span>
        </span>
      </p>
    </header>

    <!-- This disease's config.json, shared by its 3 runs: etlhub takes it only while one of them is open. -->
    <div class="input-file">
      <p class="hint">
        {{ DISEASE_NAMES[disease] }} parameters (<code>{{ CONFIG_FILES[disease] }}</code>):
        <strong :class="config?.status === 'success' ? 'text-success' : 'text-todo'">{{ FILE_STATUS[config?.status ?? 'pending'] }}</strong>
        <template v-if="!config?.launchable"> · can be changed while a run of this disease is open</template>
      </p>
      <FileDropzone
        v-model="file"
        label="config.json"
        description="Forecast parameters of this disease (JSON)"
        accept=".json,application/json"
        :server-file="isOpen ? serverFiles.config : undefined"
        :default-file="defaults[`config/${disease}`]"
        :disabled="!config?.launchable"
        :uploading="busy"
        :deleting="busy"
        @upload="upload"
        @delete="emit('delete', 'config')"
        @preview-local="f => emit('preview', 'config', f)"
        @preview-server="emit('preview', 'config', 'server')"
        @preview-default="emit('preview', 'config', { default: `config/${disease}` })"
        @use-default="emit('use-default', 'config')"
      />
    </div>

    <!-- One external_data.csv per level, shared by the 3 diseases: etlhub takes it only while a run of that level is open. -->
    <section class="external-data" :aria-labelledby="externalTitleId">
      <h4 :id="externalTitleId" class="section-title">External data <span class="hint">(shared by all diseases)</span></h4>
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
            :server-file="openLevel(state) === level.key ? serverFiles.external_data : undefined"
            :default-file="defaults[level.key]"
            :disabled="!itemOf(level.key)?.launchable"
            :uploading="busy"
            :deleting="busy"
            @upload="f => uploadExternal(level.key, f)"
            @delete="emit('delete', 'external_data')"
            @preview-local="f => emit('preview', 'external_data', f)"
            @preview-server="emit('preview', 'external_data', 'server')"
            @preview-default="emit('preview', 'external_data', { default: level.key })"
            @use-default="emit('use-default', 'external_data')"
          />
        </div>
      </div>
    </section>

    <div class="level-grid">
      <LevelColumn
        v-for="source in SOURCES"
        :key="source"
        :source="source"
        :disease="disease"
        :state="state"
        :busy="busy"
        @open="emit('open', source, disease)"
        @launch="item => emit('launch', item)"
        @validate="emit('validate')"
        @report="emit('report', source, disease)"
      />
    </div>

    <a class="next-link" :href="`#forecast-${next}`">Next disease →</a>
  </article>
</template>

<script setup lang="ts">
import { computed, reactive, ref, useId } from 'vue'
import FileDropzone from '@/views/Dashboard/components/FileDropzone.vue'
import LevelColumn from '@/views/Dashboard/components/LevelColumn.vue'
import { CONFIG_FILES, DISEASE_NAMES, FILE_STATUS, openLevel, step } from '@/config/pipeline'
import { SOURCES, type Checkpoints, type Disease, type Source } from '@/types/pipeline'
import type { DefaultFile, InputName, PreviewFrom, ServerFile } from '@/types/inputs'

const props = defineProps<{
  disease: Disease
  next: Disease
  state: Checkpoints | null
  busy: boolean
  serverFiles: Partial<Record<InputName, ServerFile>>
  defaults: Record<string, DefaultFile>
  // Returns true once uploaded: the selected file is then cleared.
  uploadFile: (name: InputName, file: File) => Promise<boolean>
}>()

const emit = defineEmits<{
  open: [source: Source, disease: Disease]
  launch: [item: string]
  validate: []
  report: [source: Source, disease: Disease]
  delete: [name: InputName]
  preview: [name: InputName, from: PreviewFrom]
  'use-default': [name: InputName]
}>()

const EXTERNAL_LEVELS = [
  { key: 'external_data/fkt', name: 'Fokontany', runs: 'ADJ or COM' },
  { key: 'external_data/csb', name: 'Health centres', runs: 'CSB' }
]

const titleId = useId()
const externalTitleId = useId()
const items = computed(() => step(props.state, 'forecast')?.items ?? [])
const itemOf = (name: string) => items.value.find(i => i.item === name)
const config = computed(() => itemOf(`config/${props.disease}`))
const published = computed(() =>
  SOURCES.filter(s => items.value.find(i => i.item === `${s}/${props.disease}:post_forecast`)?.status === 'success')
)
// input/ holds the open run's files: the server file is this disease's only when its run is open.
const isOpen = computed(() => props.state?.run?.couple.endsWith(`/${props.disease}`) ?? false)
const file = ref<File>()
const files = reactive<Record<string, File | undefined>>({})

async function upload(selected: File) {
  if (await props.uploadFile('config', selected)) file.value = undefined
}

async function uploadExternal(key: string, selected: File) {
  if (await props.uploadFile('external_data', selected)) files[key] = undefined
}
</script>
