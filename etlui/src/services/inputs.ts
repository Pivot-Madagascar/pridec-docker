import api, { withConfirm } from '@/services/api'
import type { ConfigData, CsvPreviewData, DefaultFile, InputName, ServerFile } from '@/types/inputs'

// POST /input/files/{name} (etlhub input_router): one file in the `file` field, ≤ 10 MB.
// Needs an open forecast run; confirm=true to replace a file already used (409 confirmation_required otherwise).
export async function uploadInputFile(name: InputName, file: File, confirm = false): Promise<string> {
  const body = new FormData()
  body.append('file', file)
  // The api instance defaults to JSON, which makes axios serialize FormData as JSON.
  // multipart/form-data keeps it as is; the browser then sets the boundary.
  const response = await api.post<{ saved: string }>(`/input/files/${name}`, body, {
    headers: { 'Content-Type': 'multipart/form-data' },
    ...withConfirm(confirm)
  })
  return response.data.saved
}

// GET /input/files
export async function getInputFiles(): Promise<Record<InputName, ServerFile>> {
  const response = await api.get<Record<InputName, ServerFile>>('/input/files')
  return response.data
}

// DELETE /input/files/{name}: 404 when the file is not in input/. Same confirm rule as the upload.
export async function deleteInputFile(name: InputName, confirm = false): Promise<string> {
  const response = await api.delete<{ deleted: string }>(`/input/files/${name}`, withConfirm(confirm))
  return response.data.deleted
}

// GET /input/files/config/preview: 404 absent, 422 not a JSON object.
export async function getConfigPreview(): Promise<ConfigData> {
  const response = await api.get<ConfigData>('/input/files/config/preview')
  return response.data
}

// GET /input/files/external_data/preview: first `limit` rows (1–500) + summary of the whole file.
export async function getExternalDataPreview(limit: number): Promise<CsvPreviewData> {
  const response = await api.get<CsvPreviewData>('/input/files/external_data/preview', { params: { limit } })
  return response.data
}

// GET /input/defaults: item (config/Malaria, external_data/fkt) → its default file, in the current mode.
export async function getDefaultFiles(): Promise<Record<string, DefaultFile>> {
  const response = await api.get<Record<string, DefaultFile>>('/input/defaults')
  return response.data
}

// GET /input/defaults/{item}/preview: same answer as the input/ previews; `limit` is used by CSV files only.
export async function getDefaultPreview(item: string, limit: number): Promise<ConfigData | CsvPreviewData> {
  const response = await api.get<ConfigData | CsvPreviewData>(`/input/defaults/${item}/preview`, { params: { limit } })
  return response.data
}

// POST /input/files/{name}/from-default: the open run's default copied into input/, same rules as an upload.
export async function applyDefaultFile(name: InputName, confirm = false): Promise<string> {
  const response = await api.post<{ saved: string }>(`/input/files/${name}/from-default`, null, withConfirm(confirm))
  return response.data.saved
}
