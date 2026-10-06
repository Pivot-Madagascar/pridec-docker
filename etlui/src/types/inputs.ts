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
