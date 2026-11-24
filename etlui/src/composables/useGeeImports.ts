import { ref, watch, type Ref } from 'vue'
import { getGeeImports } from '@/services/pipeline'
import { errorMessage } from '@/services/api'
import type { Checkpoints, GeeVariable } from '@/types/pipeline'

/**
 * The Import GEE dialog of Data Import: every GEE variable, whether the pass imports it, and its import state.
 * Read when the dialog opens, then at each new pipeline state while it is open: usePipeline reads it every 3 s while a
 * job runs (each variable's post shows), and after each action.
 */
export function useGeeImports(state: Ref<Checkpoints | null>) {
  const open = ref(false)
  const loading = ref(false)
  const error = ref('')
  const variables = ref<GeeVariable[] | null>(null)
  let request = 0 // only the latest answer is kept

  async function load(): Promise<void> {
    const id = ++request
    loading.value = true
    error.value = ''
    try {
      const data = await getGeeImports()
      if (id === request) variables.value = data
    } catch (err) {
      if (id === request) error.value = errorMessage(err, 'Could not read the GEE variables')
    } finally {
      if (id === request) loading.value = false
    }
  }

  watch(state, () => { if (open.value) void load() })

  function show(): void {
    open.value = true
    void load()
  }
  const close = () => { open.value = false }

  return { open, loading, error, variables, show, close, refresh: load }
}
