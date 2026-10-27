import { computed, ref, watch, type Ref } from 'vue'
import { useStorage } from '@vueuse/core'

interface PagingOptions {
  sizes: number[] // rows per page offered; 0 = all
  defaultSize: number
  sourceNewestFirst: boolean // order the server sends: reversing is enough, no date parsing, ties keep their order
}

/** Rows per page and order of one table, remembered in this browser under `etlui-table-<key>`. Newest first by default. */
export function useTablePaging<T>(key: string, items: Ref<T[]>, { sizes, defaultSize, sourceNewestFirst }: PagingOptions) {
  const settings = useStorage(`etlui-table-${key}`, { pageSize: defaultSize, newestFirst: true }, undefined, { mergeDefaults: true })
  const page = ref(0)

  const size = computed(() => (sizes.includes(settings.value.pageSize) ? settings.value.pageSize : defaultSize))
  const ordered = computed(() => (settings.value.newestFirst === sourceNewestFirst ? items.value : [...items.value].reverse()))
  const totalPages = computed(() => (size.value ? Math.max(1, Math.ceil(items.value.length / size.value)) : 1))
  const rows = computed(() => (size.value ? ordered.value.slice(page.value * size.value, (page.value + 1) * size.value) : ordered.value))

  // New data, another size or the other order: back to the first page.
  watch([items, size, () => settings.value.newestFirst], () => { page.value = 0 })

  return { settings, page, rows, totalPages }
}
