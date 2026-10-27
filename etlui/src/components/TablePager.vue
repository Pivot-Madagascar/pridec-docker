<template>
  <!-- Controls of a table paged by useTablePaging: rows per page (0 = All), order, Prev / Next. -->
  <div class="flex flex-wrap items-center justify-end gap-2 text-xs text-muted-foreground">
    <span>Rows</span>
    <!-- Reka refuses '' and numbers are fine as strings: '0' stands for All. -->
    <Select :model-value="String(pageSize)" @update:model-value="v => emit('update:pageSize', Number(v))">
      <SelectTrigger aria-label="Rows per page" size="sm" class="w-20"><SelectValue /></SelectTrigger>
      <SelectContent>
        <SelectItem v-for="s in sizes" :key="s" :value="String(s)">{{ s || 'All' }}</SelectItem>
      </SelectContent>
    </Select>
    <Button variant="outline" size="xs" data-test="order-btn" @click="emit('update:newestFirst', !newestFirst)">
      <component :is="newestFirst ? ArrowDownWideNarrow : ArrowUpNarrowWide" aria-hidden="true" />
      {{ newestFirst ? 'Newest first' : 'Oldest first' }}
    </Button>
    <template v-if="pageSize">
      <Button variant="secondary" size="xs" :disabled="page <= 0" @click="emit('update:page', page - 1)">Prev</Button>
      <span>Page {{ page + 1 }} / {{ totalPages }}</span>
      <Button variant="secondary" size="xs" :disabled="page + 1 >= totalPages" @click="emit('update:page', page + 1)">Next</Button>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ArrowDownWideNarrow, ArrowUpNarrowWide } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

defineProps<{
  sizes: number[]
  pageSize: number
  newestFirst: boolean
  page: number
  totalPages: number
}>()

const emit = defineEmits<{
  'update:pageSize': [size: number]
  'update:newestFirst': [newestFirst: boolean]
  'update:page': [page: number]
}>()
</script>
