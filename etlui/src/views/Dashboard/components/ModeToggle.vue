<template>
  <!-- Before step 1: the user's mode (their session on the server; other users keep theirs). DRYRUN: chosen for a new
       pass on Home (dryRunEditable), then fixed for the pass; etlhub's default is true in test mode, else DRYRUN of .env. -->
  <section class="mode-toggle" :class="{ 'is-test': testMode }">
    <div class="mode-text">
      <span class="mode-label">Test mode</span>
      <span class="mode-hint">
        <template v-if="testMode">Test cycle: checkpoints, runs and uploads are kept apart from production.</template>
        <template v-else>Production cycle.</template>
        Your choice only: other users keep their mode.
      </span>
      <span v-if="dryRun !== undefined" class="mode-hint" data-test="dry-run-hint" :class="{ 'mode-warn': !dryRun }">
        <template v-if="dryRun">DHIS2: dry run, the jobs write nothing.</template>
        <template v-else>DHIS2: no dry run, the jobs write to DHIS2{{ testMode ? ', even in test mode' : '' }}.</template>
      </span>
      <div v-if="dryRunEditable" class="mt-1 flex items-center gap-3">
        <span class="mode-label text-sm">Dry run</span>
        <ToggleGroup
          type="single"
          variant="outline"
          aria-label="Dry run"
          :model-value="dryRun === undefined ? undefined : dryRun ? 'yes' : 'no'"
          :disabled="disabled"
          @update:model-value="value => value && emit('dryRun', value === 'yes')"
        >
          <ToggleGroupItem v-for="choice in ['no', 'yes']" :key="choice" :value="choice" data-test="dry-run-btn"
            class="px-3.5 font-bold data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">
            {{ choice.toUpperCase() }}
          </ToggleGroupItem>
        </ToggleGroup>
      </div>
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
  dryRunEditable?: boolean // a new pass's choice (Home); read only elsewhere
  disabled?: boolean
}>()

const emit = defineEmits<{
  change: [testMode: boolean]
  dryRun: [dryRun: boolean]
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
