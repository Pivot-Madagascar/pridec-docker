<script setup lang="ts">
import type { HTMLAttributes } from "vue"
import { cn } from "cn"

const props = defineProps<{
  class?: HTMLAttributes["class"]
}>()
</script>

<template>
  <!-- etlui: no whitespace-nowrap by default (shadcn's): long values (URLs, event details) wrap; nowrap cells say so. -->
  <td
    data-slot="table-cell"
    :class="
      cn(
        'p-2 align-middle [&:has([role=checkbox])]:pr-0 *:[[role=checkbox]]:translate-y-0.5',
        props.class,
      )
    "
  >
    <slot />
  </td>
</template>
