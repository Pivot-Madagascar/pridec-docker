<template>
  <!-- The page layout of Forecast, Journal and Tracking: a side panel fixed on the left (slot `side`, optional), the page
       beside it, at the same place on every page whether or not it has a panel. -->
  <div class="side-layout">
    <aside v-if="$slots.side" class="side-panel">
      <!-- shadcn ScrollArea: the panel keeps the height of its content, and scrolls with a themed bar past the screen. -->
      <ScrollArea class="max-h-[inherit]">
        <slot name="side" />
      </ScrollArea>
    </aside>
    <slot />
  </div>
</template>

<script setup lang="ts">
import { ScrollArea } from '@/components/ui/scroll-area'
</script>

<style scoped>
@reference "../styles/base.css";

.side-layout {
  --side-width: clamp(10rem, 16vw, 20rem);
  /* ponytail: the App header is 77px (44px logo text + py-4 + 1px border, App.vue); its height in a variable if it changes.
     The panel sits 1rem under it, like every page (main's pt-4): both tops line up. */
  --side-top: calc(77px + 1rem);
  /* (100vw - 100%) / 2 = the page's own left margin (centered container): pad only what the panel (1rem from the
     edge, then a 1rem gap) still needs. 0 on a wide screen, where the margin already holds the panel. */
  padding-left: max(0px, calc(var(--side-width) + 2rem - (100vw - 100%) / 2));
}

.side-panel {
  @apply fixed left-4 z-30 flex flex-col;
  top: var(--side-top);
  max-height: calc(100vh - var(--side-top) - 1rem);
  width: var(--side-width);
}

/* The viewport is size-full (100% of an auto height): its max height makes it scroll instead of overflowing. */
.side-panel :deep([data-slot="scroll-area-viewport"]) {
  max-height: inherit;
}
</style>
