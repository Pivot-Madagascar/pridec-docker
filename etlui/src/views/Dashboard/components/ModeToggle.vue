<template>
  <!-- Before step 1: the user's mode (their session on the server; other users keep theirs). It also decides DHIS2
       writes: DRYRUN = TEST MODE (etlhub, since 2026-11-23), shown read only from etlhub's `dry_run`. -->
  <section class="mode-toggle" :class="{ 'is-test': testMode }">
    <div class="mode-text">
      <span class="mode-label">Test mode</span>
      <span class="mode-hint">
        <template v-if="testMode">Test cycle: checkpoints, runs and uploads are kept apart from production.</template>
        <template v-else>Production cycle.</template>
        Your choice only: other users keep their mode.
      </span>
      <span v-if="dryRun !== undefined" class="mode-hint" data-test="dry-run-hint" :class="{ 'mode-warn': !dryRun }">
        <template v-if="dryRun">DHIS2: dry run (test mode), the jobs write nothing.</template>
        <template v-else>DHIS2: no dry run (production), the jobs write to DHIS2.</template>
      </span>
      <span v-if="frozen" class="mode-hint" data-test="mode-frozen">
        Fixed while the pass is active: pause or abandon the cycle (left panel) to change it.
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
  dryRun: boolean | undefined // etlhub's: DRYRUN = TEST MODE
  disabled?: boolean
  frozen?: boolean // the Forecast page while its pass is active: says why it is disabled
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
