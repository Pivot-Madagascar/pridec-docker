import { describe, it, expect, beforeEach } from 'vitest'
import { nextTick, ref } from 'vue'
import { useTablePaging } from '@/composables/useTablePaging'

const OPTIONS = { sizes: [0, 2, 3], defaultSize: 2, sourceNewestFirst: false }

describe('useTablePaging', () => {
  beforeEach(() => localStorage.clear())

  it('shows the newest first by default and pages through the rows', async () => {
    const items = ref([1, 2, 3, 4, 5]) // oldest first, as the Journal receives them
    const { rows, page, totalPages } = useTablePaging('t', items, OPTIONS)
    expect(rows.value).toEqual([5, 4])
    expect(totalPages.value).toBe(3)
    page.value = 2
    expect(rows.value).toEqual([1])
  })

  it('reverses the order, shows everything with 0, and goes back to page 1 on a change', async () => {
    const items = ref([1, 2, 3, 4, 5])
    const { rows, page, settings, totalPages } = useTablePaging('t', items, OPTIONS)
    page.value = 1
    settings.value.newestFirst = false
    await nextTick()
    expect(page.value).toBe(0)
    expect(rows.value).toEqual([1, 2])
    settings.value.pageSize = 0
    await nextTick()
    expect(rows.value).toEqual([1, 2, 3, 4, 5])
    expect(totalPages.value).toBe(1)
  })

  it('keeps a source already newest first as is', () => {
    const { rows } = useTablePaging('t', ref([5, 4, 3]), { ...OPTIONS, sourceNewestFirst: true })
    expect(rows.value).toEqual([5, 4])
  })

  it('remembers the settings per table and ignores a stored size it does not offer', async () => {
    useTablePaging('a', ref([]), OPTIONS).settings.value.pageSize = 3
    await nextTick() // useStorage writes on the next tick
    expect(useTablePaging('a', ref([]), OPTIONS).settings.value.pageSize).toBe(3)
    expect(useTablePaging('b', ref([]), OPTIONS).settings.value.pageSize).toBe(2)
    localStorage.setItem('etlui-table-c', JSON.stringify({ pageSize: 7, newestFirst: false }))
    const c = useTablePaging('c', ref([1, 2, 3]), OPTIONS)
    expect(c.rows.value).toEqual([1, 2])
  })
})
