// Files managed by etlhub's /input router.
export type InputName = 'config' | 'external_data'

export interface ServerFile {
  exists: boolean
  size?: number
  modified?: string
}

// Same shape from GET /input/files/external_data/preview and from the browser stream reader.
export interface CsvPreviewData {
  columns: string[]
  rows: string[][]
  total_rows: number
  period_range: [string, string] | null
  org_units: number
}

export type ConfigData = Record<string, unknown>

// GET /input/defaults: the default file of each item (config/<disease>, external_data/<level>) in the current mode.
export interface DefaultFile {
  filename: string
  size: number
}

// What a preview reads: the server's input/ file, a selected File, or the default of an item.
export type PreviewFrom = File | 'server' | { default: string }
