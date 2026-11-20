<template>
  <!-- Full screen, above the header (z-40); the slot says what is loading. -->
  <div class="loading-screen" role="status">
    <LoaderCircle class="size-8 animate-spin" aria-hidden="true" />
    <p><slot /></p>
  </div>
</template>

<script setup lang="ts">
import { LoaderCircle } from '@lucide/vue'
</script>

<style scoped>
.loading-screen {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  background: var(--background);
  color: var(--muted-foreground);
}
</style>
