<template>
  <div class="forecast-runs" data-test="forecast-runs">
    <p class="todo" data-test="todo" role="status"><strong>To do now:</strong> {{ todo }}</p>

    <!-- The carousel has no scrollbar: these buttons (and each card's "Next disease") move between diseases. -->
    <nav class="disease-nav" data-test="disease-nav" aria-label="Diseases">
      <Button
        v-for="(disease, i) in DISEASES"
        :key="disease"
        as="a"
        size="sm"
        :variant="i === shown ? 'default' : 'outline'"
        :aria-current="i === shown ? 'true' : undefined"
        :href="`#forecast-${disease}`"
      >
        {{ DISEASE_NAMES[disease] }}
      </Button>
    </nav>
    <div class="carousel" data-test="carousel" tabindex="0" aria-label="Forecasts by disease" @scroll="onScroll">
      <DiseaseCard
        v-for="(disease, i) in DISEASES"
        :id="`forecast-${disease}`"
        :key="disease"
        :disease="disease"
        :next="DISEASES[(i + 1) % DISEASES.length]"
      />
    </div>

    <details v-if="isAdmin" class="admin-zone" data-test="admin-zone">
      <summary>Administration</summary>
      <div class="admin-actions">
        <Button variant="destructive" :disabled="busy || !state?.lock" @click="emit('release')">Release the lock</Button>
        <Button variant="destructive" :disabled="busy || !!state?.lock || !state?.run" @click="emit('abandon')">
          Abandon the open forecast run
        </Button>
      </div>
    </details>
  </div>
</template>

<script setup lang="ts">
import { computed, provide, ref } from 'vue'
import DiseaseCard from '@/views/Dashboard/components/DiseaseCard.vue'
import { Button } from '@/components/ui/button'
import { DISEASE_NAMES, ITEM_NAMES, coupleName, jobOf, labelOf, openLevel, step } from '@/config/pipeline'
import { DISEASES } from '@/types/pipeline'
import { RUNS, type RunsEmit, type RunsProps } from './runs'

const props = defineProps<RunsProps & { isAdmin: boolean }>()
const emit = defineEmits<RunsEmit & { (e: 'abandon' | 'release'): void }>()
provide(RUNS, { props, emit })

// Index of the disease card on screen: each card is 100% of the carousel width.
const shown = ref(0)
const onScroll = (e: Event) => {
  const el = e.target as HTMLElement
  shown.value = Math.round(el.scrollLeft / el.clientWidth)
}

const forecastStep = computed(() => step(props.state, 'forecast'))

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
      (i.item.startsWith(`${run.couple}:`) || i.item === `config/${disease}` || i.item === openLevel(props.state))
  )
  if (!next) return `nothing to launch for ${name}.`
  if (next.item.startsWith('config/')) return `provide the parameters of ${name} (click its card).`
  if (next.item.startsWith('external_data/')) return `provide the external data of ${name} (click its card).`
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

.forecast-runs .carousel:focus-visible,
.forecast-runs a:focus-visible,
.forecast-runs summary:focus-visible {
  outline: 2px solid #818cf8;
  outline-offset: 2px;
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
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.25rem;
  border-radius: 0.75rem;
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

/* The open run: highlighted, and the whole card is the button to its steps. */
.forecast-runs .level-column.is-open {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.12);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.35);
}

.forecast-runs .card-steps {
  position: absolute;
  inset: 0;
  border: 0;
  border-radius: inherit;
  background: transparent;
  cursor: pointer;
}

.forecast-runs .card-steps:hover {
  background: rgba(99, 102, 241, 0.1);
}

.forecast-runs .card-steps:focus-visible {
  outline: 2px solid #818cf8;
  outline-offset: 2px;
}

.forecast-runs .card-steps-hint {
  color: #a5b4fc;
  font-size: 0.8125rem;
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

/* Title (shadcn's close cross sits top right). */
.forecast-runs .steps-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

/* Stage 1: config and external data | the 3 fetches, then the data check button.
   Stage 2: forecast (+ CSB alerts) and approval | publication. 6 columns: 1, 2 or 3 items per row. */
.forecast-runs .steps-dialog .item-list {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
}

.forecast-runs .steps-dialog .item {
  grid-column: span 2;
  align-content: start;
  padding: 0.875rem;
  border-radius: 0.75rem;
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.forecast-runs .steps-dialog .item-input {
  grid-column: span 3;
}

.forecast-runs .steps-dialog .job-post_forecast {
  grid-column: 1 / -1;
}

.forecast-runs .data-check {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

/* Stage 2's Previous: where Next is in stage 1. */
.forecast-runs .tile-nav {
  display: flex;
  justify-content: flex-end;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

/* The text on the left, the data check and Next buttons together on the right. */
.forecast-runs .data-check .item-text {
  margin-right: auto;
}

/* Two per row, unless the CSB alerts make it three. */
.forecast-runs .steps-dialog .item-list:not(:has(.job-calc_orgunit_alerts)) :is(.job-forecast, .job-approve) {
  grid-column: span 3;
}

/* Narrow screens: one item per row (grid-column has no effect in a flex column). */
@media (max-width: 640px) {
  .forecast-runs .steps-dialog .item-list {
    display: flex;
  }
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

/* An input row: the dropzone takes the full width under its label. */
.forecast-runs .item-file {
  grid-column: 1 / -1;
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

.forecast-runs .level-action {
  position: relative; /* above .card-steps */
  margin-top: auto;
}

.forecast-runs .next-link {
  align-self: flex-end;
  color: #a5b4fc;
  font-weight: 600;
  padding: 0.75rem 0;
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
  .forecast-runs .level-grid {
    grid-template-columns: 1fr;
  }

  .forecast-runs .disease-card {
    padding: 1.5rem;
  }
}
</style>
