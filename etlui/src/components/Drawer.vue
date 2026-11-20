<template>
  <!-- Navigation menu of the header (shadcn Sheet: overlay, focus trap, Escape, close cross). -->
  <Sheet :open="modelValue" @update:open="emit('update:modelValue', $event)">
    <SheetContent :side="side" class="w-64 gap-0 pt-14" :aria-describedby="undefined">
      <SheetTitle class="sr-only">{{ label ?? 'Menu' }}</SheetTitle>
      <nav v-if="items.length || apiBaseUrl" class="flex flex-col gap-1 px-4 py-2">
        <router-link
          v-for="item in items"
          :key="item.to"
          :to="item.to"
          class="rounded-md px-4 py-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground [&.router-link-active]:bg-accent [&.router-link-active]:text-primary"
          @click="close"
        >
          {{ item.label }}
        </router-link>
        <a
          v-if="apiBaseUrl"
          :href="`${apiBaseUrl}/docs`"
          target="_blank"
          class="rounded-md px-4 py-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          @click="close"
        >
          API Docs
        </a>
      </nav>
    </SheetContent>
  </Sheet>
</template>

<script setup lang="ts">
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'

withDefaults(defineProps<{
  modelValue: boolean
  side?: 'left' | 'right'
  items?: { to: string; label: string }[]
  apiBaseUrl?: string
  label?: string
}>(), {
  side: 'right',
  items: () => []
})

const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const close = () => emit('update:modelValue', false)
</script>
