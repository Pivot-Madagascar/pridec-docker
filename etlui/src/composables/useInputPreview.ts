import { ref } from 'vue'
import { getConfigPreview, getDefaultPreview, getExternalDataPreview } from '@/services/inputs'
import { errorMessage } from '@/services/api'
import { previewCsvStream } from '@/utils/preview'
import type { ConfigData, CsvPreviewData, InputName, PreviewFrom } from '@/types/inputs'

export const PREVIEW_ROWS = 100

type Source = 'server' | 'local' | 'default'

async function readLocalConfig(file: File): Promise<ConfigData> {
  const data: unknown = JSON.parse(await file.text())
  if (typeof data !== 'object' || data === null || Array.isArray(data)) {
    throw new Error('config.json must be a JSON object')
  }
  return data as ConfigData
}

// Checked by shape, not instanceof File: callers (and tests) may pass any File-like object.
const isDefault = (from: PreviewFrom): from is { default: string } => typeof from === 'object' && 'default' in from

/** Preview of input/config.json or input/external_data.csv, from the server, a selected File or an item's default. */
export function useInputPreview() {
  const current = ref<{ name: InputName; source: Source } | null>(null)
  const loading = ref(false)
  const error = ref('')
  const config = ref<ConfigData | null>(null)
  const csv = ref<CsvPreviewData | null>(null)
  let request = 0 // drops answers of a preview that was replaced or closed

  const reset = () => {
    request++
    loading.value = false
    error.value = ''
    config.value = null
    csv.value = null
  }

  const open = async (name: InputName, from: PreviewFrom): Promise<void> => {
    reset()
    const id = request
    current.value = { name, source: from === 'server' ? 'server' : isDefault(from) ? 'default' : 'local' }
    loading.value = true
    try {
      if (isDefault(from)) {
        const data = await getDefaultPreview(from.default, PREVIEW_ROWS)
        if (id === request) {
          if (name === 'config') config.value = data as ConfigData
          else csv.value = data as CsvPreviewData
        }
      } else if (name === 'config') {
        const data = from === 'server' ? await getConfigPreview() : await readLocalConfig(from)
        if (id === request) config.value = data
      } else {
        const data =
          from === 'server' ? await getExternalDataPreview(PREVIEW_ROWS) : await previewCsvStream(from.stream(), PREVIEW_ROWS)
        if (id === request) csv.value = data
      }
    } catch (err) {
      if (id === request) error.value = errorMessage(err, err instanceof Error ? err.message : 'Preview failed')
    } finally {
      if (id === request) loading.value = false
    }
  }

  const close = () => {
    reset()
    current.value = null
  }

  return { current, loading, error, config, csv, open, close }
}
