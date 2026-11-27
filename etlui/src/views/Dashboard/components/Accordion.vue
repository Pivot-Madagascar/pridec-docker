<template>
  <!-- The pipeline steps of Dashboard.vue, one card each (number, title, progress), one `content-<id>` slot each. A closed
       section stays mounted (unmount-on-hide off): collapsing Forecasts must not drop the files picked but not uploaded yet. -->
  <Accordion v-model="open" type="multiple" :unmount-on-hide="false" class="space-y-4">
    <AccordionItem v-for="(item, i) in items" :key="item.id" :value="item.id" :data-section="item.id"
      class="overflow-hidden rounded-xl border bg-card shadow-sm last:border-b">
      <AccordionTrigger data-test="accordion-header" class="items-center gap-3 rounded-none px-6 py-4 hover:bg-muted/50 hover:no-underline [&>svg]:size-5">
        <span class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-sm font-bold text-primary">{{ i + 1 }}</span>
        <span class="flex-1 text-left text-lg font-bold">{{ item.title }}</span>
        <span v-if="item.progress" class="text-sm font-normal text-muted-foreground" data-test="step-progress">{{ item.progress }}</span>
      </AccordionTrigger>
      <AccordionContent class="border-t px-6 pt-4">
        <slot :name="`content-${item.id}`" />
      </AccordionContent>
    </AccordionItem>
  </Accordion>
</template>

<script setup lang="ts">
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'

defineProps<{
  items: { id: string; title: string; progress?: string }[]
}>()
// The open sections (v-model:open): the page reopens one to show its current item.
const open = defineModel<string[]>('open', { default: () => [] })
</script>
