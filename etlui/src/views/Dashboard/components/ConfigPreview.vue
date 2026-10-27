<template>
  <pre class="json-block">{{ JSON.stringify(config, null, 2) }}</pre>
</template>

<script setup lang="ts">
import type { ConfigData } from '@/types/inputs'

defineProps<{ config: ConfigData }>()
</script>

<style scoped>
@reference "../../../styles/base.css";

.json-block {
  margin: 0;
  min-height: 100%;
  padding: 1.25rem;
  overflow: auto;
  font-family: ui-monospace, monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--foreground);
  background: var(--muted);
  border-radius: 0.625rem;
  border: 1px solid var(--border);
  tab-size: 2;
}
</style>
