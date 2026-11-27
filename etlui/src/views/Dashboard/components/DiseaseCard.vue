<template>
  <!-- One disease (a tab of ForecastRuns): its 3 runs (ADJ, COM, CSB) in a carousel; their input files are in each run's "Steps" dialog. -->
  <article class="disease-card" data-test="disease-card" :aria-labelledby="titleId">
    <header class="card-header">
      <h4 :id="titleId" class="card-title">{{ DISEASE_NAMES[disease] }}</h4>
      <p class="card-progress">
        {{ published.length }} of 3 levels published
        <span class="progress-dots" aria-hidden="true">
          <span v-for="source in SOURCES" :key="source" class="progress-dot" :class="{ 'is-done': published.includes(source) }"></span>
        </span>
      </p>
    </header>

    <!-- The 3 runs side by side on a wide screen; narrower, the carousel shows fewer and its arrows move between them. -->
    <Carousel v-slot="{ canScrollPrev, canScrollNext }" :opts="{ align: 'start' }" data-test="level-carousel" :aria-label="`Runs of ${DISEASE_NAMES[disease]}`">
      <CarouselContent>
        <CarouselItem v-for="source in SOURCES" :key="source" class="md:basis-1/2 xl:basis-1/3">
          <LevelColumn :source="source" :disease="disease" />
        </CarouselItem>
      </CarouselContent>
      <div v-if="canScrollPrev || canScrollNext" class="mt-4 flex justify-end gap-2">
        <CarouselPrevious class="static translate-y-0" />
        <CarouselNext class="static translate-y-0" />
      </div>
    </Carousel>
  </article>
</template>

<script setup lang="ts">
import { computed, inject, useId } from 'vue'
import LevelColumn from '@/views/Dashboard/components/LevelColumn.vue'
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious } from '@/components/ui/carousel'
import { DISEASE_NAMES, step } from '@/config/pipeline'
import { SOURCES, type Disease } from '@/types/pipeline'
import { RUNS } from './runs'

const props = defineProps<{ disease: Disease }>()
const runs = inject(RUNS)!.props

const titleId = useId()
const items = computed(() => step(runs.state, 'forecast')?.items ?? [])
const published = computed(() =>
  SOURCES.filter(s => items.value.find(i => i.item === `${s}/${props.disease}:post_forecast`)?.status === 'success')
)
</script>
