<template>
  <!-- System follows the OS live; the choice is remembered in this browser (`etlui-theme`). Never empty. -->
  <ToggleGroup
    type="single"
    size="sm"
    aria-label="Theme"
    :model-value="store"
    @update:model-value="value => value && (store = value as typeof store)"
  >
    <ToggleGroupItem v-for="t in THEMES" :key="t.value" :value="t.value" :aria-label="t.label" :title="t.label">
      <component :is="t.icon" />
    </ToggleGroupItem>
  </ToggleGroup>
</template>

<script setup lang="ts">
import { useColorMode } from '@vueuse/core'
import { Monitor, Moon, Sun } from '@lucide/vue'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'

// `.dark` on <html> drives the shadcn tokens of styles/base.css.
const { store } = useColorMode({ storageKey: 'etlui-theme' })

const THEMES = [
  { value: 'auto', label: 'System theme', icon: Monitor },
  { value: 'light', label: 'Light theme', icon: Sun },
  { value: 'dark', label: 'Dark theme', icon: Moon }
] as const
</script>
