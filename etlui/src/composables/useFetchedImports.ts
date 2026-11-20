import { computed, ref, watch, type Ref } from 'vue'
import { storeToRefs } from 'pinia'
import { step } from '@/config/pipeline'
import { useFetchedImportsStore } from '@/stores/fetchedImports'
import type { Checkpoints } from '@/types/pipeline'

/**
 * The imports approval dialog of Data Import: the Pivot data elements fetched in this pass, kept in Pinia.
 * Read again only when it may have changed (an import_pivot_* job finished, another pass or mode) or on Refresh;
 * reopening the dialog shows what was read.
 */
export function useFetchedImports(state: Ref<Checkpoints | null>) {
  const store = useFetchedImportsStore()
  const { imports, loading, error } = storeToRefs(store)
  const open = ref(false)

  // What the files depend on; null while a Pivot import runs (its files are being replaced).
  const stamp = computed(() => {
    const s = state.value
    if (!s) return null
    const pivot = step(s, 'data_import')?.items.filter(i => i.item.startsWith('import_pivot_')) ?? []
    if (pivot.some(i => i.status === 'running')) return null
    return [s.test_mode, s.pass?.id, ...pivot.map(i => `${i.item}:${i.status}:${i.job_id}:${i.updated_at}`)].join('|')
  })

  // Read once already: follow the changes. Never read: wait for the first show().
  watch(stamp, s => {
    if (s !== null && store.stamp !== null && s !== store.stamp) void store.load(s)
  })

  function show(): void {
    open.value = true
    const s = stamp.value ?? store.stamp
    if (s !== store.stamp || (imports.value === null && !loading.value)) void store.load(s)
  }

  const refresh = () => store.load(stamp.value ?? store.stamp)
  const close = () => { open.value = false }

  return { open, loading, error, imports, show, refresh, close }
}
