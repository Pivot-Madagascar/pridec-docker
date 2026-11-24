<template>
  <div class="flex flex-col gap-6" :lang="lang">
    <Item class="p-0" data-test="page-header">
      <ItemContent>
        <ItemTitle><h2 class="text-2xl font-bold">{{ lang === 'fr' ? 'Aide' : 'Help' }}</h2></ItemTitle>
        <ItemDescription class="line-clamp-none">{{ t.description }}</ItemDescription>
      </ItemContent>
      <ItemActions>
        <!-- The language to read, remembered in this browser. -->
        <ToggleGroup v-model="lang" type="single" variant="outline" size="sm" aria-label="Language / Langue" data-test="help-lang">
          <ToggleGroupItem value="en" lang="en" class="px-3 data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">English</ToggleGroupItem>
          <ToggleGroupItem value="fr" lang="fr" class="px-3 data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">Français</ToggleGroupItem>
        </ToggleGroup>
      </ItemActions>
    </Item>

    <Card class="p-6" data-test="how-it-works">
      <h3 class="text-lg font-semibold">{{ t.howTitle }}</h3>
      <ol class="list-decimal space-y-2 pl-5 text-sm">
        <li v-for="(line, i) in t.how" :key="i">
          <span v-html="line" />
          <ul v-if="i === 2" class="mt-1 list-disc space-y-1 pl-5">
            <li v-for="step in t.steps" :key="step" v-html="step" />
          </ul>
        </li>
      </ol>
      <p class="text-sm text-muted-foreground">{{ t.rules }}</p>
    </Card>

    <Card class="p-6" data-test="glossary">
      <h3 class="text-lg font-semibold">{{ t.glossaryTitle }}</h3>
      <dl class="divide-y text-sm">
        <div v-for="g in t.glossary" :id="`term-${g.id}`" :key="g.id" class="grid gap-1 py-3 sm:grid-cols-[14rem_1fr] sm:gap-4">
          <dt class="font-semibold">{{ g.term }}</dt>
          <dd class="text-muted-foreground">{{ g.def }}</dd>
        </div>
      </dl>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useStorage } from '@vueuse/core'
import { Card } from '@/components/ui/card'
import { Item, ItemActions, ItemContent, ItemDescription, ItemTitle } from '@/components/ui/item'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { HELP, type Lang } from './content'

// The browser's language at first, then the reader's choice. A click on the active choice sends '': keep the language.
const stored = useStorage<Lang>('etlui-help-lang', navigator.language.startsWith('fr') ? 'fr' : 'en')
const lang = computed({ get: () => (stored.value === 'fr' ? 'fr' : 'en'), set: v => { if (v) stored.value = v } })
const t = computed(() => HELP[lang.value])
</script>
