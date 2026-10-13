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
        :disabled="!config?.launchable"
        :uploading="busy"
        :deleting="busy"
        @upload="upload"
        @delete="emit('delete', 'config')"
        @preview-local="f => emit('preview', 'config', f)"
        @preview-server="emit('preview', 'config', 'server')"
      />
    </div>

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
import { computed, ref, useId } from 'vue'
import FileDropzone from '@/views/Dashboard/components/FileDropzone.vue'
import LevelColumn from '@/views/Dashboard/components/LevelColumn.vue'
import { CONFIG_FILES, DISEASE_NAMES, FILE_STATUS, step } from '@/config/pipeline'
import { SOURCES, type Checkpoints, type Disease, type Source } from '@/types/pipeline'
import type { InputName, ServerFile } from '@/types/inputs'

const props = defineProps<{
  disease: Disease
  next: Disease
  state: Checkpoints | null
  busy: boolean
  serverFiles: Partial<Record<InputName, ServerFile>>
  // Returns true once uploaded: the selected file is then cleared.
  uploadFile: (name: InputName, file: File) => Promise<boolean>
}>()

const emit = defineEmits<{
  open: [source: Source, disease: Disease]
  launch: [item: string]
  validate: []
  report: [source: Source, disease: Disease]
  delete: [name: InputName]
  preview: [name: InputName, from: File | 'server']
}>()

const titleId = useId()
const items = computed(() => step(props.state, 'forecast')?.items ?? [])
const config = computed(() => items.value.find(i => i.item === `config/${props.disease}`))
const published = computed(() =>
  SOURCES.filter(s => items.value.find(i => i.item === `${s}/${props.disease}:post_forecast`)?.status === 'success')
)
// input/ holds the open run's files: the server file is this disease's only when its run is open.
const isOpen = computed(() => props.state?.run?.couple.endsWith(`/${props.disease}`) ?? false)
const file = ref<File>()

async function upload(selected: File) {
  if (await props.uploadFile('config', selected)) file.value = undefined
}
</script>
