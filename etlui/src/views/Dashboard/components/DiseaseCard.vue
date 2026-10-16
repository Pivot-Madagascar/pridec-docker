<template>
  <!-- One disease: its 3 runs (ADJ, COM, CSB) side by side; their input files are in each run's "Steps" dialog. -->
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

    <div class="level-grid">
      <LevelColumn
        v-for="source in SOURCES"
        :key="source"
        :source="source"
        :disease="disease"
        :state="state"
        :busy="busy"
        :server-files="serverFiles"
        :defaults="defaults"
        :upload-file="uploadFile"
        @open="emit('open', source, disease)"
        @launch="item => emit('launch', item)"
        @validate="emit('validate')"
        @report="emit('report', source, disease)"
        @delete="name => emit('delete', name)"
        @preview="(name, from) => emit('preview', name, from)"
        @use-default="name => emit('use-default', name)"
      />
    </div>

    <a class="next-link" :href="`#forecast-${next}`">Next disease →</a>
  </article>
</template>

<script setup lang="ts">
import { computed, useId } from 'vue'
import LevelColumn from '@/views/Dashboard/components/LevelColumn.vue'
import { DISEASE_NAMES, step } from '@/config/pipeline'
import { SOURCES, type Checkpoints, type Disease, type Source } from '@/types/pipeline'
import type { DefaultFile, InputName, PreviewFrom, ServerFile } from '@/types/inputs'

const props = defineProps<{
  disease: Disease
  next: Disease
  state: Checkpoints | null
  busy: boolean
  serverFiles: Partial<Record<InputName, ServerFile>>
  defaults: Record<string, DefaultFile>
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

const titleId = useId()
const items = computed(() => step(props.state, 'forecast')?.items ?? [])
const published = computed(() =>
  SOURCES.filter(s => items.value.find(i => i.item === `${s}/${props.disease}:post_forecast`)?.status === 'success')
)
</script>
