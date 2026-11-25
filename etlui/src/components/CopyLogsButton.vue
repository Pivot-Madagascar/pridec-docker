<template>
  <!-- Floats at the top right of a logs box (its parent: `relative`, outside the scrolling area, so it stays put). -->
  <Button
    variant="secondary"
    size="icon-sm"
    class="absolute right-3 top-3 z-10 shadow-sm"
    data-test="copy-logs"
    :disabled="!text"
    :aria-label="copied ? 'Logs copied' : 'Copy the logs'"
    :title="copied ? 'Copied' : 'Copy the logs'"
    @click="copy(text)"
  >
    <Check v-if="copied" class="text-success" aria-hidden="true" />
    <Copy v-else aria-hidden="true" />
  </Button>
</template>

<script setup lang="ts">
import { useClipboard } from '@vueuse/core'
import { Check, Copy } from '@lucide/vue'
import { Button } from '@/components/ui/button'

defineProps<{ text: string }>() // the logs shown, copied as they are
// legacy: execCommand when the Clipboard API is missing (etlui served over plain http is not a secure context).
const { copy, copied } = useClipboard({ legacy: true })
</script>
