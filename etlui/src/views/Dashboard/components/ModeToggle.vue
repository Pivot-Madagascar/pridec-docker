<template>
  <!-- Before step 1: the mode applies to the whole cycle (TEST_MODE on the server). DHIS2 writes follow DRYRUN (.env). -->
  <section class="mode-toggle" :class="{ 'is-test': testMode }">
    <div class="mode-text">
      <span class="mode-label">Test mode</span>
      <span class="mode-hint">
        <template v-if="testMode">Test cycle: checkpoints, runs and uploads are kept apart from production.</template>
        <template v-else>Production cycle.</template>
      </span>
      <!-- Read only: DRYRUN is set in the root .env, not here -->
      <span v-if="dryRun !== undefined" class="mode-hint" :class="{ 'mode-warn': testMode && !dryRun }">
        <template v-if="dryRun">DHIS2: DRYRUN on (.env), nothing is written.</template>
        <template v-else>DHIS2: DRYRUN off (.env), jobs write to DHIS2{{ testMode ? ', even in test mode' : '' }}.</template>
      </span>
    </div>
    <!-- Single choice, never empty: clicking the active item again changes nothing. -->
    <ToggleGroup
      type="single"
      variant="outline"
      aria-label="Test mode"
      :model-value="testMode === undefined ? undefined : testMode ? 'yes' : 'no'"
      :disabled="disabled"
      @update:model-value="value => value && emit('change', value === 'yes')"
    >
      <ToggleGroupItem v-for="choice in ['no', 'yes']" :key="choice" :value="choice" data-test="mode-btn"
        class="px-3.5 font-bold data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">
        {{ choice.toUpperCase() }}
      </ToggleGroupItem>
    </ToggleGroup>
  </section>
</template>

<script setup lang="ts">
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'

defineProps<{
  testMode: boolean | undefined // unknown until the first read of the state
  dryRun: boolean | undefined
  disabled?: boolean
}>()

const emit = defineEmits<{
  change: [testMode: boolean]
}>()
</script>

<style scoped>
@reference "../../../styles/base.css";

.mode-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.25rem;
  margin-bottom: 1.5rem;
  border-radius: 0.75rem;
  background: var(--card);
  border: 1px solid var(--border);
}

.mode-toggle.is-test {
  border-color: color-mix(in oklab, var(--warning) 50%, transparent);
  background: color-mix(in oklab, var(--warning) 8%, transparent);
}

.mode-text {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.mode-label {
  font-weight: 700;
  color: var(--foreground);
}

.mode-hint {
  font-size: 0.8125rem;
  color: var(--muted-foreground);
}

.mode-hint.mode-warn {
  color: var(--destructive);
}
</style>
