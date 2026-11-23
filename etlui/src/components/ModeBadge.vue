<template>
  <!-- The header's reminder of the user's mode, on every page: test mode = DRYRUN (nothing written to DHIS2),
       production = real DHIS2 writes. Read only: the mode is changed on Home or the Forecast page (ModeToggle). -->
  <Badge
    v-if="auth.isAuthenticated && mode.testMode !== null"
    data-test="mode-badge"
    variant="outline"
    class="font-bold"
    :class="mode.testMode ? 'border-warning bg-warning/10 text-warning' : 'border-destructive bg-destructive/10 text-destructive'"
    :title="mode.dryRun ? 'DHIS2 dry run: the jobs write nothing' : 'The jobs write to DHIS2'"
  >
    {{ mode.testMode ? 'TEST MODE' : 'PRODUCTION' }} · {{ mode.dryRun ? 'DRYRUN' : 'DHIS2 writes' }}
  </Badge>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { Badge } from '@/components/ui/badge'
import { useAuthStore } from '@/stores/auth'
import { useModeStore } from '@/stores/mode'

const auth = useAuthStore()
const mode = useModeStore()

// At login (a session starts in test mode) and on another user's login; logged out: forget the mode.
watch(() => auth.user?.id, id => (id ? mode.load() : mode.set(null)), { immediate: true })
</script>
