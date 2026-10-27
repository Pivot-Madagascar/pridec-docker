<template>
  <!-- The pipeline steps of Dashboard.vue, one `content-<id>` slot each. A closed section stays mounted
       (unmount-on-hide off): collapsing Forecasts must not drop the files picked but not uploaded yet. -->
  <Accordion type="multiple" :default-value="defaultOpen" :unmount-on-hide="false" class="overflow-hidden rounded-2xl border bg-card shadow-2xl">
    <AccordionItem v-for="item in items" :key="item.id" :value="item.id">
      <AccordionTrigger data-test="accordion-header" class="items-center rounded-none bg-muted/50 p-6 text-xl font-bold hover:bg-muted hover:no-underline [&>svg]:size-5">
        {{ item.title }}
      </AccordionTrigger>
      <AccordionContent class="px-6 pt-4">
        <slot :name="`content-${item.id}`" />
      </AccordionContent>
    </AccordionItem>
  </Accordion>
</template>

<script setup lang="ts">
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'

defineProps<{
  items: { id: string; title: string }[]
  defaultOpen?: string[]
}>()
</script>
