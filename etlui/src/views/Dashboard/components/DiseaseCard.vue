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
      />
    </div>

    <a class="next-link" :href="`#forecast-${next}`">Next disease →</a>
  </article>
</template>

<script setup lang="ts">
import { computed, inject, useId } from 'vue'
import LevelColumn from '@/views/Dashboard/components/LevelColumn.vue'
import { DISEASE_NAMES, step } from '@/config/pipeline'
import { SOURCES, type Disease } from '@/types/pipeline'
import { RUNS } from './runs'

const props = defineProps<{ disease: Disease; next: Disease }>()
const runs = inject(RUNS)!.props

const titleId = useId()
const items = computed(() => step(runs.state, 'forecast')?.items ?? [])
const published = computed(() =>
  SOURCES.filter(s => items.value.find(i => i.item === `${s}/${props.disease}:post_forecast`)?.status === 'success')
)
</script>
