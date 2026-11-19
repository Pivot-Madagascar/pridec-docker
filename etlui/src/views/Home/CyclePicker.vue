<template>
  <Popover v-model:open="open">
    <PopoverTrigger as-child>
      <Button variant="outline" type="button" :disabled="disabled" :value="model" data-test="cycle-picker" class="w-56 justify-start font-normal">
        <CalendarIcon />
        {{ label }}
      </Button>
    </PopoverTrigger>
    <PopoverContent class="w-auto p-0">
      <!-- Months only: shadcn has no month picker, reka's is styled like shadcn's Calendar. -->
      <MonthPickerRoot
        v-slot="{ grid }"
        :model-value="value"
        :default-placeholder="value"
        :max-value="max"
        :locale="locale"
        prevent-deselect
        initial-focus
        class="p-3"
        @update:model-value="pick"
      >
        <MonthPickerHeader class="flex items-center justify-between">
          <MonthPickerPrev :class="cn(buttonVariants({ variant: 'outline' }), 'size-7 p-0')"><ChevronLeft class="size-4" /></MonthPickerPrev>
          <MonthPickerHeading class="text-sm font-medium" />
          <MonthPickerNext :class="cn(buttonVariants({ variant: 'outline' }), 'size-7 p-0')"><ChevronRight class="size-4" /></MonthPickerNext>
        </MonthPickerHeader>
        <MonthPickerGrid class="mt-3">
          <MonthPickerGridBody>
            <MonthPickerGridRow v-for="(row, i) in grid.rows" :key="i" class="flex gap-1 mt-1">
              <MonthPickerCell v-for="m in row" :key="m.toString()" :date="m">
                <MonthPickerCellTrigger :month="m" :class="cellClass" />
              </MonthPickerCell>
            </MonthPickerGridRow>
          </MonthPickerGridBody>
        </MonthPickerGrid>
      </MonthPickerRoot>
    </PopoverContent>
  </Popover>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { endOfMonth, getLocalTimeZone, parseDate, today, type DateValue } from '@internationalized/date'
import { CalendarIcon, ChevronLeft, ChevronRight } from '@lucide/vue'
import {
  MonthPickerCell, MonthPickerCellTrigger, MonthPickerGrid, MonthPickerGridBody, MonthPickerGridRow,
  MonthPickerHeader, MonthPickerHeading, MonthPickerNext, MonthPickerPrev, MonthPickerRoot
} from 'reka-ui'
import { cn } from '@/lib/utils'
import { Button, buttonVariants } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

// The cycle as 'YYYY-MM'. The server refuses a future month.
const model = defineModel<string>({ required: true })
defineProps<{ disabled?: boolean }>()

const open = ref(false)
const locale = Intl.DateTimeFormat().resolvedOptions().locale // the same language as the label
const value = computed(() => parseDate(`${model.value}-01`))
const max = endOfMonth(today(getLocalTimeZone()))
const label = computed(() =>
  value.value.toDate(getLocalTimeZone()).toLocaleDateString(locale, { month: 'long', year: 'numeric' }))
// The look of shadcn's CalendarCellTrigger, wider for a month name.
const cellClass = cn(
  buttonVariants({ variant: 'ghost' }),
  'h-8 w-16 p-0 font-normal capitalize',
  '[&[data-today]:not([data-selected])]:bg-accent [&[data-today]:not([data-selected])]:text-accent-foreground',
  'data-[selected]:bg-primary data-[selected]:text-primary-foreground [&[data-selected]:hover]:bg-primary data-[selected]:hover:text-primary-foreground',
  'data-[disabled]:text-muted-foreground data-[disabled]:opacity-50'
)

function pick(month: DateValue | DateValue[] | undefined): void {
  if (!month || Array.isArray(month)) return
  model.value = `${month.year}-${String(month.month).padStart(2, '0')}`
  open.value = false
}
</script>
