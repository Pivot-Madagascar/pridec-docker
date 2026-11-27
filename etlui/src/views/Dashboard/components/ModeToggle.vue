<template>
  <!-- The user's mode (their session on the server; other users keep theirs), as a shadcn Card (the Forecast page's
       first fact card). It also decides DHIS2 writes: DRYRUN = TEST MODE (etlhub, since 2026-11-23), shown read only
       from etlhub's `dry_run`. -->
  <Card class="gap-3 py-4" :class="{ 'border-warning/50 bg-warning/8': testMode }" data-test="mode-card">
    <CardHeader class="px-4">
      <CardDescription>Mode</CardDescription>
      <CardTitle class="text-xl">{{ testMode === undefined ? '…' : testMode ? 'Test' : 'Production' }}</CardTitle>
      <CardAction class="flex flex-col items-end gap-1">
        <span class="text-xs text-muted-foreground">Test mode</span>
        <!-- Single choice, never empty: clicking the active item again changes nothing. -->
        <ToggleGroup
          type="single"
          variant="outline"
          size="sm"
          aria-label="Test mode"
          :model-value="testMode === undefined ? undefined : testMode ? 'yes' : 'no'"
          :disabled="disabled"
          @update:model-value="value => value && emit('change', value === 'yes')"
        >
          <ToggleGroupItem v-for="choice in ['no', 'yes']" :key="choice" :value="choice" data-test="mode-btn"
            class="px-3 font-bold data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">
            {{ choice.toUpperCase() }}
          </ToggleGroupItem>
        </ToggleGroup>
      </CardAction>
    </CardHeader>
    <CardContent class="flex flex-col gap-1 px-4 text-xs text-muted-foreground">
      <span>
        <template v-if="testMode">Test cycle: checkpoints, runs and uploads are kept apart from production.</template>
        <template v-else>Production cycle.</template>
        Your choice only: other users keep their mode.
      </span>
      <span v-if="dryRun !== undefined" data-test="dry-run-hint" :class="{ 'text-destructive': !dryRun }">
        <template v-if="dryRun">DHIS2: dry run (test mode), the jobs write nothing.</template>
        <template v-else>DHIS2: no dry run (production), the jobs write to DHIS2.</template>
      </span>
      <span v-if="frozen" data-test="mode-frozen">
        Fixed while the pass is active: pause or abandon the cycle (top of the page) to change it.
      </span>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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
