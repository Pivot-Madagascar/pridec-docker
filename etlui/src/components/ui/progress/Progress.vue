<script setup lang="ts">
import type { ProgressRootProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { computed } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { cn } from "cn"
import {
  ProgressIndicator,
  ProgressRoot,
} from "reka-ui"

const props = withDefaults(
  defineProps<ProgressRootProps & { class?: HTMLAttributes["class"] }>(),
  {
    modelValue: 0,
  },
)

const delegatedProps = reactiveOmit(props, "class")
// etlui: shadcn's indicator assumed max = 100; a run's bar is "3 of 9 steps".
const percent = computed(() => ((props.modelValue ?? 0) / (props.max ?? 100)) * 100)
</script>

<template>
  <ProgressRoot
    data-slot="progress"
    v-bind="delegatedProps"
    :class="
      cn(
        'bg-primary/20 relative h-2 w-full overflow-hidden rounded-full',
        props.class,
      )
    "
  >
    <ProgressIndicator
      data-slot="progress-indicator"
      class="bg-primary h-full w-full flex-1 transition-all"
      :style="`transform: translateX(-${100 - percent}%);`"
    />
  </ProgressRoot>
</template>
